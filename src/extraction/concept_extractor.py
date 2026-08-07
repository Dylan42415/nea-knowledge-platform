"""
Concept Extraction Module.
Extracts environmental entities, pollutants, guidelines, and metrics.
Delegates to Gold Extractor for AI generation and rule-based heuristic extraction.
"""
import re
from typing import List, Dict, Any

from src.extraction.gold_extractor import extract_gold_notes

KNOWN_POLLUTANTS_AND_CONCEPTS = [
    "Pollutant Standards Index", "PSI", "PM2.5", "PM10", "Particulate Matter", 
    "Benzene", "Sulphur Dioxide", "SO2", "Nitrogen Dioxide", "NO2", "Carbon Monoxide", 
    "CO", "Ozone", "O3", "Lead", "Dioxins", "Enterococcus", "Dissolved Oxygen", "DO",
    "Total Suspended Solids", "TSS", "Biochemical Oxygen Demand", "BOD",
    "Microplastics", "Marine Litter", "Short-term Beach Water Quality Information System",
    "BSWI", "Vehicle Emissions Scheme", "VES", "COVID-19 Circuit Breaker",
    "National Environment Agency", "NEA", "WHO Air Quality Guidelines", "WHO AQG"
]

def extract_concepts_fallback(text: str) -> List[Dict[str, Any]]:
    """
    Rule-based environmental entity extraction fallback.
    Matches actual pollutants, metrics, and agencies with exact sentence excerpts.
    """
    entities: List[Dict[str, Any]] = []
    text_lower = text.lower()
    sentences = [s.strip() for s in re.split(r'[.\n]+', text) if s.strip()]

    for term in KNOWN_POLLUTANTS_AND_CONCEPTS:
        if re.search(r'\b' + re.escape(term.lower()) + r'\b', text_lower):
            # Find relevant sentence excerpt containing term
            rel_sentences = [s for s in sentences if term.lower() in s.lower()]
            summary = " ".join(rel_sentences[:2]) if rel_sentences else f"Environmental metric/concept: {term}."
            
            # Extract numbers and units if present
            numbers = re.findall(r'\b\d+(?:\.\d+)?\s*(?:ppb|µg/m³|mg/l|mg/Nm³|%)\b', summary)
            key_data = ""
            if numbers:
                key_data = f"| Parameter | Extracted Metric |\n|---|---|\n| {term} | {', '.join(numbers)} |"

            entities.append({
                "title": term,
                "name": term,
                "type": "Concept",
                "summary": summary,
                "source_location": "Extracted from document text",
                "key_data": key_data,
                "relationships": [{"predicate": "MONITORED_BY", "target": "National Environment Agency"}],
                "excerpt": rel_sentences[0] if rel_sentences else summary
            })

    return entities

def extract_concepts(text: str, source_context: str = '') -> List[Dict[str, Any]]:
    """
    Extract Gold Standard concepts from text using Gold Extractor with rule-based fallback.
    """
    payload = {
        "title": source_context or "Extracted Document Topic",
        "content": text,
        "source_document": source_context,
        "source_location": "document text"
    }
    gold_notes = extract_gold_notes(payload)
    if gold_notes and gold_notes[0].get("summary") != "Extracted via fallback mechanism":
        return gold_notes
    return extract_concepts_fallback(text)
