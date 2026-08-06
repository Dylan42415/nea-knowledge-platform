"""
Gold Standard Knowledge Extraction Engine.
Converts section payloads into structured wiki notes matching gold_standard_example.md.
"""
import time
import json
import yaml
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
1. MAXIMIZE REAL CONTENT: If the source contains tables, charts, lists, named thresholds, dates, 10-year trends, or specific findings, extract ALL of them into GFM Markdown tables under "## Key Data / Findings". Copy all numbers, units, and dates exactly.
2. ADAPTIVE STRUCTURE: Include only sections supported by evidence:
   - ## Summary (1-3 data-dense sentences)
   - ## Key Data / Findings (FULL Markdown tables for thresholds, advisory bands, trends, statistics)
   - ## Relationships (Typed bold predicates: - **COMPUTED_FROM** → ..., - **BENCHMARKED_AGAINST** → ..., - **MANAGED_BY** → ...)
   - ## Source Excerpt (Verbatim quote with page citation: > "quote..." \n — source_document, source_location)
3. NO PLACEHOLDERS: Do NOT invent generic text. Every claim must trace to the source text.
4. EXACT UNITS: Copy units, dates, and qualifiers exactly (e.g., "0.28 ppb", "5 mg/Nm³", "1% by volume").
5. OUTPUT FORMAT: Output ONLY valid JSON containing a list of note objects:
[
  {
    "title": "Pollutant Standards Index",
    "type": "Concept",
    "source_document": "soe_report.pdf",
    "source_location": "pp. 6-7, 'Pollutant Standards Index (PSI)' section",
    "summary": "...",
    "key_data": "**Health Advisory Bands (24-hour PSI Descriptor):**\\n\\n| PSI Range | Descriptor | Guidance |\\n|---|---|---|\\n...",
    "relationships": [
      {"predicate": "COMPUTED_FROM", "target": "PM10, PM2.5, SO2, NO2, CO, O3"},
      {"predicate": "BENCHMARKED_AGAINST", "target": "WHO Air Quality Guidelines (2005)"}
    ],
    "excerpt": "The PSI is an index to provide easily understandable information..."
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
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                time.sleep(2)
                continue
            time.sleep(1)

    return _heuristic_gold_fallback(topic_payload)

def _heuristic_gold_fallback(topic_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Local heuristic fallback when Gemini API is rate-limited."""
    title = topic_payload.get("title", "Extracted Topic").strip()
    content = topic_payload.get("content", "")
    source_doc = topic_payload.get("source_document", "")
    source_loc = topic_payload.get("source_location", "")

    summary_lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")][:3]
    summary = " ".join(summary_lines) if summary_lines else f"Extracted knowledge regarding {title}."

    return [
        {
            "title": title,
            "type": "Concept",
            "source_document": source_doc,
            "source_location": source_loc,
            "summary": summary,
            "key_data": "",
            "relationships": [],
            "excerpt": summary[:200]
        }
    ]
