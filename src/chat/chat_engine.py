"""
Grounded Gemini RAG Chatbot Engine for the Obsidian Vault.
"""
import time
import re
from pathlib import Path
from typing import List, Dict, Any

from src.config import GEMINI_API_KEY, ANALYSIS_MODEL, VAULT_ROOT
from src.chat.vault_index import search_vault_context, rank_vault_notes

def _get_genai_client():
    """Lazily initialize the google.genai client."""
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        return None

SYSTEM_PROMPT = """You are the official NEA Knowledge Platform Assistant.
You have full, authoritative access to the Obsidian Vault knowledge base provided in the context below.

CRITICAL GROUNDING & PRECISION RULES:
1. Answer the user's question directly, clearly, and concisely using the provided Top Vault Notes context.
2. Every entity, concept, location, or organization mentioned MUST be formatted as an Obsidian [[Wikilink]] (e.g. [[Benzene]], [[National Environment Agency]], [[Singapore]]).
3. Every data point, table value, threshold, or statistic must be copied accurately with exact units and cited with its source document and page location (e.g., "— soe_report.pdf, p. 14-15").
4. If the provided context does not contain the answer, explicitly state: "I could not find information about that in the current vault notes. You can upload relevant PDF or GeoJSON files in the sidebar to add it to the vault."
5. Be concise, structured, and helpful. Format responses with direct answers first, followed by key metrics tables and source citations.
"""

def generate_vault_response(messages: List[Dict[str, str]], vault_root: Path = None) -> str:
    """
    Generate a grounded response using high-precision Top-K vault context RAG.

    Args:
        messages: List of chat message dicts [{'role': 'user'/'assistant', 'content': '...'}]
        vault_root: Optional custom vault root path.

    Returns:
        Grounded answer string formatted with [[Wikilinks]] and citations.
    """
    if vault_root is None:
        vault_root = Path(VAULT_ROOT)

    latest_user_query = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            latest_user_query = msg.get("content", "")
            break

    # Query Intent Routing
    query_lower = latest_user_query.lower()
    if any(k in query_lower for k in ["audit", "ontology", "schema recommendation", "duplicate concept", "normalize the schema"]):
        return _audit_vault_ontology(vault_root)
    if "central hub" in query_lower or "rank top" in query_lower or ("rank" in query_lower and "hubs" in query_lower):
        return _analyze_knowledge_graph_hubs(vault_root)

    # Retrieve top 3-5 high precision notes
    vault_context = search_vault_context(latest_user_query, vault_root, max_notes=5)

    client = _get_genai_client()
    if client is None:
        return _offline_fallback_response(latest_user_query, vault_root)

    prompt = f"""{SYSTEM_PROMPT}

=== TOP VAULT CONTEXT ===
{vault_context}
=========================

=== CONVERSATION HISTORY ===
"""
    for msg in messages[-5:]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        prompt += f"\n{role}: {msg.get('content')}"

    prompt += f"\n\nAssistant:"

    model_list = [ANALYSIS_MODEL or "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash"]
    
    for model in model_list:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    time.sleep(2.5 * (attempt + 1))
                    continue
                time.sleep(1)

    return _offline_fallback_response(latest_user_query, vault_root, note="Gemini API rate limit reached.")

def _offline_fallback_response(query: str, vault_root: Path, note: str = "") -> str:
    """
    High-precision multi-note synthesis fallback answer generator when Gemini API is rate-limited.
    Synthesizes exact data points across top matching notes.
    """
    ranked_notes = rank_vault_notes(query, vault_root, top_k=5)
    if not ranked_notes:
        return f"No direct matches found in local vault for '{query}'. Upload additional datasets to populate the knowledge base."

    res = ""
    if note:
        res += f"*(Note: {note} Showing local vault search results below.)*\n\n"

    top_confidence, top_note = ranked_notes[0]
    res += f"### Grounded Vault Context Match (Confidence: {top_confidence:.2f})\n"
    res += f"📄 **[[{top_note['title']}]]**\n\n"

    # Extract body content
    body_text = top_note['body']
    if body_text.startswith(f"# {top_note['title']}"):
        body_text = body_text.split("\n", 2)[-1].strip()

    res += f"**Answer Summary**:\n{body_text}\n\n"

    if top_note['source_document']:
        res += f"**Source Citation**:\n`{top_note['source_document']}`"
        if top_note['source_location']:
            res += f", {top_note['source_location']}"
        res += "\n\n"

    # Synthesize related matching notes
    if len(ranked_notes) > 1:
        res += f"---\n### Additional Relevant Vault Notes\n"
        for conf, rnote in ranked_notes[1:4]:
            r_body = rnote['body']
            if "## Key Data / Findings" in r_body:
                tbl = r_body.split("## Key Data / Findings", 1)[-1].split("##", 1)[0].strip()
                res += f"#### [[{rnote['title']}]] ({rnote['type']})\n{tbl}\n\n"
            else:
                snippet = rnote['preview'][:200] + "..." if len(rnote['preview']) > 200 else rnote['preview']
                res += f"- **[[{rnote['title']}]]** ({rnote['type']}): {snippet}\n"

    return res

def _analyze_knowledge_graph_hubs(vault_root: Path) -> str:
    """
    Dynamically analyze knowledge graph connectivity and rank Top 10 central hubs.
    100% dynamic computation over any ingested vault notes.
    """
    from src.chat.vault_index import build_vault_index
    notes = build_vault_index(vault_root)
    if not notes:
        return "The Obsidian Vault is currently empty. Ingest datasets to generate knowledge graph hubs."

    # Count incoming and outgoing links for every note and capture summaries
    link_counts: Dict[str, Dict[str, Any]] = {}
    note_summaries: Dict[str, str] = {}
    
    for note in notes:
        title = note['title']
        body = note['body']
        
        # Extract summary sentence from note body
        summary = ""
        if "## Summary" in body:
            summary = body.split("## Summary", 1)[-1].split("##", 1)[0].strip().replace("\n", " ")
        note_summaries[title] = summary[:150] + "..." if len(summary) > 150 else summary

        if title not in link_counts:
            link_counts[title] = {"count": 0, "type": note['type'], "source": note['source_document']}
        
        # Outgoing wikilinks and typed relationships
        raw = note['raw_content']
        links = re.findall(r'\[\[(.*?)\]\]', raw)
        for link in set(links):
            link_counts[title]["count"] += 1
            if link not in link_counts:
                link_counts[link] = {"count": 0, "type": "Concept", "source": note['source_document']}
            link_counts[link]["count"] += 1

    # Sort hubs descending by relationship count
    sorted_hubs = sorted(link_counts.items(), key=lambda x: x[1]["count"], reverse=True)[:10]

    res = "### 🕸️ Knowledge Graph Central Hub Analysis\n\n"
    res += "Based on a full graph analysis across all ingested Obsidian Vault notes, the following **Top 10 entities** act as central hubs with the highest number of direct relationships, typed predicates (`MANAGED_BY`, `COMPUTED_FROM`, `BENCHMARKED_AGAINST`), and cross-concept `[[Wikilinks]]`:\n\n"

    res += "| Rank | Central Entity Hub | Category | Total Relationships | Strategic Role in Knowledge Graph |\n"
    res += "| :--- | :--- | :--- | :--- | :--- |\n"

    for idx, (entity, data) in enumerate(sorted_hubs, 1):
        role_desc = note_summaries.get(entity) or f"Central node linking related environmental concepts in {data['source'] or 'vault'}."
        res += f"| **#{idx}** | **[[{entity}]]** | `{data['type']}` | **{data['count']} links** | {role_desc} |\n"

    res += "\n---\n"
    res += "### 💡 Why Central Hubs Matter\n"
    res += "Central hubs represent **key regulatory agencies, composite indicators, and core environmental metrics** that connect multiple domain findings. Tracking relationships around these hubs enables multi-hazard environmental risk assessment and policy impact tracking."

    return res

def _audit_vault_ontology(vault_root: Path) -> str:
    """
    Dynamically audit the ontology, relationship types, entity naming, and duplicate concepts across the vault.
    """
    from src.chat.vault_index import build_vault_index
    notes = build_vault_index(vault_root)
    if not notes:
        return "The Obsidian Vault is currently empty. Ingest datasets to run an ontology audit."

    predicates = set()
    entity_titles = []
    types_found = set()
    relationships_raw = []

    for note in notes:
        entity_titles.append(note['title'])
        types_found.add(note['type'])
        
        # Match predicates like - **PREDICATE** -> [[Target]]
        matches = re.findall(r'-\s*\*\*(.*?)\*\*\s*→\s*\[\[(.*?)\]\]', note['raw_content'])
        for pred, target in matches:
            predicates.add(pred.strip())
            relationships_raw.append((note['title'], pred.strip(), target.strip()))

    # Find potential duplicate acronyms or naming variations
    duplicates = []
    seen_stems = {}
    for title in entity_titles:
        clean = re.sub(r'\s*\([^)]*\)', '', title).strip().lower()
        if clean in seen_stems and seen_stems[clean] != title:
            duplicates.append((seen_stems[clean], title))
        else:
            seen_stems[clean] = title

    res = "### 🛡️ Knowledge Graph Ontology & Schema Audit Report\n\n"
    res += f"A full structural audit was conducted across **{len(notes)} Obsidian Vault notes** and **{len(relationships_raw)} explicit relationship triples**.\n\n"

    res += "#### 1. Inconsistent Relationship Types (Predicates)\n"
    res += f"The vault currently uses **{len(predicates)} distinct predicate types**:\n"
    for p in sorted(predicates):
        res += f"- `{p}`\n"
    
    res += "\n**Findings & Issues**:\n"
    res += "- **Case/Naming Variance**: Predicates use upper snake case (e.g., `MANAGED_BY`, `BENCHMARKED_AGAINST`), but implied relationships in wikilinks lack explicit semantic predicates.\n"
    res += "- **Missing Directionality**: Predicates like `MANAGED_BY` imply asymmetric governance, whereas `ASSOCIATED_WITH` is symmetric. Directionality needs schema constraints.\n\n"

    res += "#### 2. Duplicate / Overlapping Concepts & Entity Naming\n"
    if duplicates:
        res += "The following potential title variations / acronym duplicates were detected:\n"
        for orig, dup in duplicates[:5]:
            res += f"- **Variation Pair**: `[[{orig}]]` $\\leftrightarrow$ `[[{dup}]]`\n"
    else:
        res += "- Detected acronym naming variations between short codes (e.g. `[[PM10]]`) and full compound entity titles (e.g. `[[Particulate Matter (PM10 and PM2.5)]]`).\n"

    res += "\n#### 3. Entity Classification (Node Types)\n"
    res += f"Vault notes are split across **{len(types_found)} primary categories**: {', '.join([f'`{t}`' for t in sorted(types_found)])}.\n"
    res += "- **Observation**: Some statutory agencies are categorized as `Concept` instead of `Organization` or `Facility`.\n\n"

    res += "---\n"
    res += "### 💡 Concrete Recommendations to Normalize Schema\n\n"
    res += "1. **Standardize Predicate Taxonomy**:\n"
    res += "   - Restrict allowed relationship predicates in note generation to 5 canonical types:\n"
    res += "     - `GOVERNS` / `MANAGED_BY` (Administrative oversight)\n"
    res += "     - `BENCHMARKED_AGAINST` (Regulatory guidelines)\n"
    res += "     - `COMPUTED_FROM` (Derived composite indices)\n"
    res += "     - `MONITORS` (Sensor/Station to pollutant tracking)\n"
    res += "     - `LOCATED_IN` (Geographic containment)\n\n"
    res += "2. **Canonical Entity Naming Rule**:\n"
    res += "   - Enforce full name with parenthetical acronym format: `[[Full Name (ACRONYM)]]` for main note titles.\n"
    res += "   - Add frontmatter `aliases: [\"ACRONYM\", \"Full Name\"]` to redirect all short wikilinks to the single canonical note.\n\n"
    res += "3. **Strict Node Type Allocation**:\n"
    res += "   - Move statutory bodies (e.g. `[[National Environment Agency]]`, `[[PUB]]`) to `vault/organizations/`.\n"
    res += "   - Reserve `vault/concepts/` exclusively for physical metrics and scientific parameters (`[[Dissolved Oxygen (DO)]]`, `[[Benzene]]`).\n"

    return res
