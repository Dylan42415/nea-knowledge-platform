"""
Gold Standard Knowledge Extraction Engine.
Converts section payloads into structured wiki notes matching gold_standard_example.md.
"""
import time
import json
import yaml
import re
from pathlib import Path
from typing import List, Dict, Any

from src.config import GEMINI_API_KEY, ANALYSIS_MODEL
from src.vault_writer.note_generator import sanitize_filename

def _get_genai_client():
    """Lazily initialize the google.genai client."""
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        return None

SYSTEM_PROMPT = """You are a knowledge extraction engine that converts source document text into structured Gold Standard Obsidian wiki notes.

CRITICAL RULES:
1. EXTRACT ALL NAMED POLLUTANTS & ENTITIES: You MUST create a separate, dedicated note object for EVERY named pollutant, concept, indicator, or facility mentioned in the text (e.g. Benzene, Ozone (O3), PM2.5, PM10, SO2, NO2, CO, Lead, Dioxins, Inland Water Quality, Coastal Water Quality, Microplastics, Haze Monitoring). Do NOT omit any specific pollutant or entity.
2. MAXIMIZE REAL CONTENT: Extract ALL raw numbers, 10-year annual means, 2020 performance metrics, WHO guidelines, thresholds, and statistics into GFM Markdown tables under "## Key Data / Findings".
3. ADAPTIVE STRUCTURE: Include only sections supported by evidence:
   - ## Summary (1-3 data-dense sentences)
   - ## Key Data / Findings (FULL Markdown tables for thresholds, advisory bands, trends, statistics)
   - ## Relationships (Typed bold predicates: - **COMPUTED_FROM** → ..., - **BENCHMARKED_AGAINST** → ..., - **MANAGED_BY** → ...)
   - ## Source Excerpt (Verbatim quote with page citation: > "quote..." \n — source_document, source_location)
4. NO PLACEHOLDERS: Do NOT invent generic text. Every claim must trace to the source text.
5. EXACT UNITS: Copy units, dates, and qualifiers exactly (e.g., "0.28 ppb", "5 mg/Nm³", "1% by volume", "0.5 µg/m³").
6. OUTPUT FORMAT: Output ONLY valid JSON containing a list of note objects:
[
  {
    "title": "Benzene",
    "type": "Concept",
    "source_document": "soe_report.pdf",
    "source_location": "pp. 14-15, 'BENZENE' section",
    "summary": "Benzene is a volatile organic compound (VOC) monitored in Singapore due to its carcinogenicity. In 2020, the average ambient concentration was 0.28 ppb, the lowest since monitoring began in 2015.",
    "key_data": "| Parameter | Value | Benchmark |\n|---|---|---|\n| 2020 Annual Mean | 0.28 ppb | EU Guidelines (0.3 - 0.5 ppb) |\n| Emission Limit | 5 mg/Nm³ | NEA Industrial Regulation |\n| Petrol Content Limit | 1% by volume | Implemented 2017 |",
    "relationships": [
      {"predicate": "MANAGED_BY", "target": "National Environment Agency"},
      {"predicate": "BENCHMARKED_AGAINST", "target": "EU Benzene Guidelines"}
    ],
    "excerpt": "The average ambient benzene concentration in 2020 was 0.28 ppb, the lowest recorded since monitoring began in 2015."
  }
]
"""

def extract_gold_notes(topic_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract Gold Standard note payloads from a topic section payload using Gemini AI.

    Args:
        topic_payload: Dict with 'title', 'content', 'source_document', 'source_location'.

    Returns:
        List of Gold Standard note dictionaries matching gold_standard_example.md schema.
    """
    client = _get_genai_client()
    if client is None:
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

    model_list = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.5-flash"]
    
    for model in model_list:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            res_text = response.text.strip()
            if res_text.startswith("```json"):
                res_text = res_text[7:]
            if res_text.startswith("```"):
                res_text = res_text[3:]
            if res_text.endswith("```"):
                res_text = res_text[:-3]

            notes_data = json.loads(res_text.strip())
            if isinstance(notes_data, list):
                for note in notes_data:
                    if not note.get("source_document"):
                        note["source_document"] = source_doc
                    if not note.get("source_location"):
                        note["source_location"] = source_loc
                return notes_data
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "503" in err_msg:
                time.sleep(6)
                continue
            time.sleep(2)

    return _heuristic_gold_fallback(topic_payload)

def _heuristic_gold_fallback(topic_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    High-density local heuristic fallback when Gemini API is rate-limited.
    Parses tables, numerical metrics, and entity relationships deterministically.
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

    # Build relationships
    relationships = []
    if "national environment agency" in content.lower() or "nea" in content.lower():
        relationships.append({"predicate": "MANAGED_BY", "target": "National Environment Agency"})
    if "who" in content.lower() or "world health" in content.lower():
        relationships.append({"predicate": "BENCHMARKED_AGAINST", "target": "WHO Air Quality Guidelines"})

    return [
        {
            "title": title,
            "type": "Concept",
            "source_document": source_doc,
            "source_location": source_loc,
            "summary": summary,
            "key_data": key_data,
            "relationships": relationships,
            "excerpt": sentences[0] if sentences else summary[:200]
        }
    ]
