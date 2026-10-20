"""
Gold Standard Knowledge Extraction Engine.
Converts section payloads into structured wiki notes matching gold_standard_example.md.
"""
import time
import json
import yaml
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import GEMINI_API_KEY, ANALYSIS_MODEL
from src.vault_writer.note_generator import sanitize_filename

logger = logging.getLogger(__name__)

def _get_genai_client():
    """Lazily initialize the google.genai client."""
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        logger.debug("Could not initialize google.genai client: %s", e)
        return None

SYSTEM_PROMPT = """You are an advanced knowledge extraction engine that converts environmental source texts (acts, circulars, reports, and datasets) into structured Gold Standard Obsidian wiki notes.

CRITICAL RULES:
1. EXHAUSTIVE DYNAMIC ENTITY DISCOVERY: Extract a dedicated, separate note object for EVERY discrete named concept, environmental pollutant, statutory regulation, indicator, or facility identified in the text across any domain (air quality, marine/water quality, noise limits, waste management, vector control, carbon emissions, radiation). Never skip specific named entities.
2. MAXIMIZE REAL CONTENT & DATA TABLES: Extract ALL raw statistics, baseline averages, thresholds, numerical standards, and monitoring trends into GFM Markdown tables under "## Key Data / Findings".
3. AUTONOMOUS BLINDSPOT & KNOWLEDGE GAP DISCOVERY ("Hole Finder"):
   - For every extracted note, actively audit the evidence to find missing data, unanchored claims, and surveillance blindspots.
   - Detect missing temporal coverage (e.g. unstated observation years, unverified historical trends).
   - Detect missing regulatory benchmarks, unstated emission thresholds, or undefined testing methodologies.
   - List these specifically in a dedicated "knowledge_gaps" array.
4. UNRESOLVED GRAPH TARGETS:
   - When an entity refers to a missing authority, unstated regulation, or unmonitored baseline, generate an explicit unresolved wikilink target formatted as "Unresolved: <Description of Missing Data>" in the relationships array with predicate "IDENTIFIES_GAP" (e.g., target="Unresolved: Ambient Limit for Acrolein").
5. ADAPTIVE STRUCTURE: Include only sections supported by evidence:
   - ## Summary (1-3 data-dense sentences)
   - ## Key Data / Findings (FULL Markdown tables for thresholds, advisory bands, trends, statistics)
   - ## Relationships (Typed bold predicates: - **COMPUTED_FROM** → ..., - **BENCHMARKED_AGAINST** → ..., - **MANAGED_BY** → ..., - **IDENTIFIES_GAP** → ...)
   - ## Knowledge Gaps & Unresolved Blindspots (Flagged omissions and missing data)
   - ## Source Excerpt (Verbatim quote with page citation: > "quote..." \n — source_document, source_location)
6. EXACT UNITS & ZERO PLACEHOLDERS: Copy units, dates, and qualifiers exactly (e.g., "0.28 ppb", "5 mg/Nm³", "1% by volume", "0.5 µg/m³"). Do not invent generic filler.
7. OUTPUT FORMAT: Output ONLY valid JSON containing a list of note objects:
[
  {
    "title": "Clean Entity Title",
    "type": "Concept",
    "source_document": "source_filename.pdf",
    "source_location": "pp. 14-15",
    "summary": "1-3 concise, fact-dense sentences grounded in evidence.",
    "key_data": "| Parameter | Value | Benchmark |\n|---|---|---|",
    "relationships": [
      {"predicate": "MANAGED_BY", "target": "National Environment Agency"},
      {"predicate": "IDENTIFIES_GAP", "target": "Unresolved: 2021-2023 Monitoring Trend"}
    ],
    "knowledge_gaps": [
      "No longitudinal monitoring data reported after 2020.",
      "Regulatory standard for non-industrial zones is omitted."
    ],
    "excerpt": "Verbatim quote from source document."
  }
]
"""

def extract_gold_notes(topic_payload: Dict[str, Any], strict_live: bool = False) -> List[Dict[str, Any]]:
    """
    Extract Gold Standard note payloads from a topic section payload using Gemini AI.

    Args:
        topic_payload: Dict with 'title', 'content', 'source_document', 'source_location'.
        strict_live: When True, disallows silent fallback and raises RuntimeError if live LLM fails.

    Returns:
        List of Gold Standard note dictionaries matching gold_standard_example.md schema.
    """
    client = _get_genai_client()
    if client is None:
        if strict_live:
            raise RuntimeError("Gemini GenAI client not initialized (missing API key or client error) in strict live mode.")
        logger.warning("Gemini GenAI client not available; invoking local deterministic heuristic fallback.")
        return _heuristic_gold_fallback(topic_payload)

    source_doc = topic_payload.get("source_document", "document.pdf")
    source_loc = topic_payload.get("source_location", "p. 1")
    content = topic_payload.get("content", "")

    prompt = f"""{SYSTEM_PROMPT}

=== SOURCE PAYLOAD ===
Source Document: {source_doc}
Source Location: {source_loc}

Text Content:
{content}
======================

Extract all major concepts, datasets, locations, and organizations into Gold Standard notes JSON:"""

    candidate_models = [ANALYSIS_MODEL, "gemini-2.0-flash", "gemini-1.5-flash"]
    model_list = []
    for m in candidate_models:
        if m and m not in model_list:
            model_list.append(m)
    
    last_error: Optional[Exception] = None
    for model in model_list:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            res_text = response.text.strip()
            
            # Robust JSON extraction: match JSON array [ ... ] or object { ... }
            json_match = re.search(r"\[\s*\{.*\}\s*\]", res_text, re.DOTALL)
            if json_match:
                notes_data = json.loads(json_match.group(0))
            else:
                single_match = re.search(r"\{\s*\".*\}\s*", res_text, re.DOTALL)
                if single_match:
                    parsed = json.loads(single_match.group(0))
                    notes_data = [parsed] if isinstance(parsed, dict) else parsed
                else:
                    clean_text = re.sub(r"^```(?:json)?\s*", "", res_text, flags=re.MULTILINE)
                    clean_text = re.sub(r"```\s*$", "", clean_text, flags=re.MULTILINE).strip()
                    notes_data = json.loads(clean_text)

            if isinstance(notes_data, list):
                for note in notes_data:
                    if not note.get("source_document"):
                        note["source_document"] = source_doc
                    if not note.get("source_location"):
                        note["source_location"] = source_loc
                    if "knowledge_gaps" not in note:
                        note["knowledge_gaps"] = []
                    # Provenance tracking: tag with live model source
                    note["extraction_source"] = f"gemini:{model}"
                return notes_data
        except Exception as e:
            last_error = e
            err_msg = str(e)
            logger.error("Gemini model '%s' extraction failed: %s", model, err_msg)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "503" in err_msg:
                time.sleep(4)
                continue
            time.sleep(1)

    if strict_live:
        raise RuntimeError(f"All Gemini extraction models {model_list} failed in strict live mode. Last error: {last_error}")

    logger.warning("All Gemini candidate models %s failed. Falling back to deterministic heuristic extractor.", model_list)
    return _heuristic_gold_fallback(topic_payload)

def _heuristic_gold_fallback(topic_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    High-density local heuristic fallback when Gemini API is rate-limited.
    Parses tables, numerical metrics, entity relationships, and active blindspots deterministically.
    """
    title = topic_payload.get("title", "Extracted Topic").strip()
    if not title or title.isdigit() or title.lower() in ["foreword", "contents", "table of contents"]:
        return []

    content = topic_payload.get("content", "")
    source_doc = topic_payload.get("source_document", "")
    source_loc = topic_payload.get("source_location", "")

    sentences = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
    summary = " ".join(sentences[:3]) if sentences else f"Environmental monitoring data regarding {title}."

    # Extract numerical statistics and metrics with units
    metrics = re.findall(r'\b[A-Za-z0-9\.\-\s]{2,30}\b:\s*\b\d+(?:\.\d+)?\s*(?:ppb|µg/m³|mg/l|mg/Nm³|%|counts/100\s*ml)\b', content, re.IGNORECASE)
    
    # Extract markdown tables if present in section content
    table_lines = [line for line in content.splitlines() if "|" in line]
    key_data = ""
    if len(table_lines) >= 2:
        key_data = "\n".join(table_lines)
    elif metrics:
        rows = [f"| Metric {i+1} | {m.strip()} | Extracted from {source_doc} |" for i, m in enumerate(metrics[:6])]
        key_data = "| Indicator / Parameter | Value / Standard | Note |\n|---|---|---|\n" + "\n".join(rows)

    # Build relationships dynamically from text payload
    relationships = []
    found_links = re.findall(r'\[\[(.*?)\]\]', content)
    for fl in found_links:
        target = fl.split('|')[0].strip()
        if target and target.lower() != title.lower():
            relationships.append({
                "predicate": "REFERENCES",
                "target": target,
                "notes": f"Linked in context of {title}"
            })

    # Dynamically extract statutory instruments, governing bodies, and standards via regex
    dynamic_acts = re.findall(r'\b[A-Z][A-Za-z0-9\s]{2,40}(?:Act|Regulation|Standard|Order|Bylaw|Directive|Guidelines)\b', content)
    dynamic_orgs = re.findall(r'\b[A-Z][A-Za-z0-9\s]{2,40}(?:Agency|Board|Authority|Ministry|Department|Commission|Organization|Administration)\b', content)
    candidate_gov = list(dict.fromkeys(dynamic_acts + dynamic_orgs))
    for ent in candidate_gov:
        ent_clean = ent.strip()
        if ent_clean.lower() != title.lower() and len(ent_clean) > 3:
            if not any(r["target"].lower() == ent_clean.lower() for r in relationships):
                is_gov = any(w in ent_clean.lower() for w in ["act", "regulation", "order", "bylaw", "agency", "board", "ministry"])
                relationships.append({
                    "predicate": "GOVERNED_BY" if is_gov else "BENCHMARKED_AGAINST",
                    "target": ent_clean,
                    "notes": f"Dynamically extracted statutory framework from {source_doc}"
                })

    # Extract uppercase agency / standards acronyms (e.g. WHO, PUB, NEA, USEPA, ISO) dynamically
    acronyms = set(re.findall(r'\b[A-Z]{3,6}\b', content))
    excluded_acronyms = {"THE", "AND", "FOR", "NOT", "PDF", "SEE", "PPM", "PPB"}
    for acr in acronyms:
        if acr not in excluded_acronyms and acr.lower() != title.lower() and not any(r["target"].upper() == acr for r in relationships):
            relationships.append({
                "predicate": "BENCHMARKED_AGAINST",
                "target": acr,
                "notes": f"Acronym benchmark extracted from {source_doc}"
            })

    # Active Blindspot & Hole Finding ("Hole Finder")
    knowledge_gaps = []
    if not metrics and not table_lines:
        knowledge_gaps.append(f"No quantitative numerical benchmarks, concentrations, or emission limits specified for {title}.")
    has_year = bool(re.search(r'\b(19\d\d|20\d\d)\b', content))
    if not has_year:
        knowledge_gaps.append("Temporal observation window, baseline year, or monitoring date not explicitly reported.")
    has_gov = any(r.get("predicate") in ["GOVERNED_BY", "MANAGED_BY"] for r in relationships)
    if not has_gov:
        gap_target = f"Unresolved: Regulatory Authority for {title}"
        relationships.append({
            "predicate": "IDENTIFIES_GAP",
            "target": gap_target,
            "notes": "No specific statutory enforcement authority or act cited"
        })
        knowledge_gaps.append(f"Statutory oversight authority or governing bylaw not stated in {source_doc}.")

    return [
        {
            "title": title,
            "type": "Concept",
            "source_document": source_doc,
            "source_location": source_loc,
            "summary": summary,
            "key_data": key_data,
            "relationships": relationships,
            "knowledge_gaps": knowledge_gaps,
            "excerpt": sentences[0] if sentences else summary[:200],
            "extraction_source": "heuristic_fallback"
        }
    ]

