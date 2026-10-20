"""
Grounded Gemini RAG Chatbot Engine for the Obsidian Vault.
"""
import time
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import GEMINI_API_KEY, ANALYSIS_MODEL, VAULT_ROOT
from src.chat.vault_index import search_vault_context, rank_vault_notes, is_stub_note, expand_graph_neighborhood

logger = logging.getLogger(__name__)

def _get_genai_client():
    """Lazily initialize the google.genai client."""
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        logger.debug("Could not initialize google.genai client: %s", e)
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

def generate_vault_response(messages: List[Dict[str, str]], vault_root: Path = None, strict_live: bool = False) -> str:
    """
    Generate a grounded response using high-precision Top-K vault context RAG.

    Args:
        messages: List of chat message dicts [{'role': 'user'/'assistant', 'content': '...'}]
        vault_root: Optional custom vault root path.
        strict_live: When True, disallows silent fallback and raises RuntimeError if live LLM fails.

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

    # Calculate query confidence score (0.00 to 1.00) from vault ranker
    ranked_top = rank_vault_notes(latest_user_query, vault_root, top_k=1)
    confidence = ranked_top[0][0] if ranked_top else 0.00
    confidence_header = f"📊 **Confidence Score**: `{confidence:.2f}` / `1.00`\n\n"

    # Check if user specifically requests knowledge graph network hubs or ontology structural audit
    query_lower = latest_user_query.lower()
    is_ontology_audit = any(p in query_lower for p in ["audit ontology", "ontology audit", "audit the ontology", "schema recommendation", "normalize the schema", "audit vault ontology"])
    is_graph_hubs_query = any(p in query_lower for p in ["central hubs in the knowledge graph", "top 10 central hubs", "network analysis", "graph hub analysis"])

    # Dynamic Retrieval Window Scaling
    is_broad_query = any(k in query_lower for k in ["all", "summary", "overview", "every", "data points", "everything", "list", "metrics"])
    max_notes = 12 if is_broad_query else 8

    # Dynamic Graph-RAG Retrieval: BM25 + 2-hop neighborhood expansion
    vault_context = search_vault_context(latest_user_query, vault_root, max_notes=max_notes)

    # If asking specifically about graph topology or ontology, compute dynamic analytics
    graph_analytics_context = ""
    if is_ontology_audit:
        graph_analytics_context = f"\n=== KNOWLEDGE GRAPH ONTOLOGY AUDIT DATA ===\n{_audit_vault_ontology(vault_root)}\n"
    elif is_graph_hubs_query:
        graph_analytics_context = f"\n=== KNOWLEDGE GRAPH CENTRAL HUBS DATA ===\n{_analyze_knowledge_graph_hubs(vault_root)}\n"

    client = _get_genai_client()
    if client is None:
        if strict_live:
            raise RuntimeError("Gemini GenAI client not initialized (missing API key or client error) in strict live mode.")
        if is_ontology_audit:
            return confidence_header + _audit_vault_ontology(vault_root)
        if is_graph_hubs_query:
            return confidence_header + _analyze_knowledge_graph_hubs(vault_root)
        logger.warning("Gemini GenAI client not available; falling back to offline vault synthesis response.")
        return confidence_header + _offline_fallback_response(
            latest_user_query, 
            vault_root, 
            note="Gemini client uninitialized (missing API key or client setup error)."
        )

    prompt = f"""{SYSTEM_PROMPT}

=== TOP VAULT CONTEXT ===
{vault_context}
{graph_analytics_context}
=========================

=== CONVERSATION HISTORY ===
"""
    for msg in messages[-5:]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        prompt += f"\n{role}: {msg.get('content')}"

    prompt += f"\n\nAssistant:"

    candidate_models = [ANALYSIS_MODEL, "gemini-3-flash-preview", "gemini-3.6-flash", "gemini-3.1-flash-lite"]
    model_list = []
    for m in candidate_models:
        if m and m not in model_list:
            model_list.append(m)
    
    last_error: Optional[Exception] = None
    for model in model_list:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                if response and response.text:
                    ans_text = response.text.strip()
                    # Ensure confidence header is at the top if not already included
                    if "Confidence Score" not in ans_text:
                        ans_text = f"{confidence_header}{ans_text}"
                    return ans_text
            except Exception as e:
                last_error = e
                err_msg = str(e)
                logger.error("Gemini model '%s' generation attempt %d failed: %s", model, attempt + 1, err_msg)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    time.sleep(2.5 * (attempt + 1))
                    continue
                time.sleep(1)

    if strict_live:
        raise RuntimeError(f"All Gemini models {model_list} failed in strict live mode. Last error: {last_error}")

    logger.warning("All candidate models %s failed. Falling back to offline vault synthesis.", model_list)
    return confidence_header + _offline_fallback_response(
        latest_user_query, 
        vault_root, 
        note=f"All candidate Gemini models {model_list} failed or reached rate limits."
    )


def _offline_fallback_response(query: str, vault_root: Path, note: str = "") -> str:
    """
    High-precision multi-note synthesis fallback answer generator when Gemini API is rate-limited.
    Uses stub filtering and graph neighborhood expansion to ensure data-rich leaf notes are surfaced.
    Always includes a prominent banner stating that the response is an offline local extraction without LLM.
    """
    reason_detail = f" (**Reason:** {note})" if note else ""
    offline_banner = (
        "> ⚠️ **OFFLINE FALLBACK MODE (LOCAL VAULT RETRIEVAL — NO LIVE LLM)**\n"
        f"> **Notice**: The live Gemini model endpoint was unavailable{reason_detail}. "
        "The response below was deterministically assembled directly from your local Obsidian Knowledge Graph vault notes without generative AI reasoning.\n\n"
        "---\n\n"
    )

    ranked_notes = rank_vault_notes(query, vault_root, top_k=8)
    if not ranked_notes:
        return (
            offline_banner
            + f"No direct matches found in local vault for '{query}'. Upload additional datasets to populate the knowledge base."
        )

    # Filter out empty stub notes from primary response slot
    non_stub_notes = [(conf, n) for conf, n in ranked_notes if not is_stub_note(n)]

    # If top ranked matches are all empty stubs, use graph expansion to discover connected leaf notes
    if not non_stub_notes:
        expanded = expand_graph_neighborhood(query, vault_root, top_seeds=3, max_depth=2, max_total_notes=6)
        for item in expanded:
            note_dict = item.get("note", {})
            if not is_stub_note(note_dict):
                non_stub_notes.append((item.get("confidence", 0.75), note_dict))

    active_notes = non_stub_notes if non_stub_notes else ranked_notes

    res = offline_banner

    top_confidence, top_note = active_notes[0]
    res += f"### 📄 Grounded Vault Match: **[[{top_note['title']}]]** (Confidence: {top_confidence:.2f})\n\n"

    # Extract body content
    body_text = top_note['body']
    if body_text.startswith(f"# {top_note['title']}"):
        body_text = body_text.split("\n", 2)[-1].strip()

    res += f"**Answer Summary**:\n{body_text}\n\n"

    if top_note.get('source_document'):
        res += f"**Source Citation**:\n`{top_note['source_document']}`"
        if top_note.get('source_location'):
            res += f", {top_note['source_location']}"
        res += "\n\n"

    # Synthesize related matching notes from active non-stub candidates
    if len(active_notes) > 1:
        res += f"---\n### Additional Relevant Vault Notes\n"
        for conf, rnote in active_notes[1:4]:
            r_body = rnote.get('body', '')
            if "## Key Data / Findings" in r_body:
                tbl = r_body.split("## Key Data / Findings", 1)[-1].split("##", 1)[0].strip()
                res += f"#### [[{rnote['title']}]] ({rnote.get('type', 'Concept')})\n{tbl}\n\n"
            else:
                preview_text = rnote.get('preview') or r_body[:200].replace('\n', ' ').strip()
                snippet = preview_text + "..." if len(preview_text) >= 200 else preview_text
                res += f"- **[[{rnote['title']}]]** ({rnote.get('type', 'Concept')}): {snippet}\n"

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

    res += "#### 1. Discovered Relationship Types (Predicates)\n"
    res += f"The vault currently uses **{len(predicates)} distinct predicate types**:\n"
    if predicates:
        for p in sorted(predicates):
            res += f"- `{p}`\n"
    else:
        res += "- No formal typed predicates found. Relationships are expressed primarily via implicit `[[Wikilinks]]`.\n"

    res += "\n#### 2. Duplicate / Overlapping Concepts & Entity Naming\n"
    if duplicates:
        res += f"Detected **{len(duplicates)} potential title variation pairs** in the current notes:\n"
        for orig, dup in duplicates[:8]:
            res += f"- **Variation Pair**: `[[{orig}]]` $\\leftrightarrow$ `[[{dup}]]`\n"
    else:
        res += "No duplicate naming variations or unaliased acronym pairs detected among current vault entities.\n"

    res += "\n#### 3. Entity Classification (Node Types)\n"
    res += f"Vault notes are distributed across **{len(types_found)} primary categories**: {', '.join([f'`{t}`' for t in sorted(types_found)])}.\n\n"

    res += "---\n"
    res += "### 💡 Dynamic Schema Normalization Insights\n\n"
    if predicates:
        res += f"1. **Predicate Consolidation**: Audit identified {len(predicates)} active predicates. Ensure predicates follow canonical active/passive directions.\n"
    else:
        res += "1. **Predicate Enrichment**: Upgrade implicit `[[Wikilinks]]` to typed semantic predicates (`MANAGED_BY`, `BENCHMARKED_AGAINST`, etc.).\n"

    if duplicates:
        res += f"2. **Alias Unification**: Merge the {len(duplicates)} candidate duplicate pairs by adding YAML frontmatter `aliases` to the canonical notes.\n"
    else:
        res += "2. **Canonical Naming**: Maintain the 1:1 entity naming standard across newly ingested circulars.\n"

    res += "3. **Type Segregation**: Ensure statutory bodies reside in `vault/organizations/` and physical metrics in `vault/concepts/`.\n"

    return res
