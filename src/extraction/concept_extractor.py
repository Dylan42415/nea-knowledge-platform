"""
Concept Extraction Module.
Extracts environmental entities, pollutants, guidelines, and metrics.
Delegates to Gold Extractor for AI generation and rule-based heuristic extraction.
"""
import re
from typing import List, Dict, Any

from src.extraction.gold_extractor import extract_gold_notes

def extract_concepts_fallback(text: str) -> List[Dict[str, Any]]:
    """
    Domain-agnostic entity extraction fallback.
    Dynamically identifies capitalized technical terms, acronyms, and section metrics.
    """
    entities: List[Dict[str, Any]] = []
    if not text.strip():
        return entities

    sentences = [s.strip() for s in re.split(r'[.\n]+', text) if s.strip()]
    
    # Dynamically extract candidate capitalized entities & acronyms
    candidate_terms = set(re.findall(r'\b[A-Z][A-Za-z0-9\.\-\(\)\/]{1,30}(?:\s+[A-Z][A-Za-z0-9\.\-\(\)\/]{1,30})*\b', text))
    
    # Filter common stop words / generic sentence starters
    stop_words = {"The", "In", "On", "At", "For", "With", "By", "An", "A", "This", "That", "These", "Those", "Over", "Under", "Figure", "Table", "Page", "Section", "NEA"}
    valid_terms = [t for t in candidate_terms if t not in stop_words and len(t) > 2]

    for term in valid_terms:
        rel_sentences = [s for s in sentences if term.lower() in s.lower()]
        summary = " ".join(rel_sentences[:2]) if rel_sentences else f"Extracted parameter/concept: {term}."
        
        # Extract numbers and units if present
        numbers = re.findall(r'\b\d+(?:\.\d+)?\s*(?:[a-zA-Z0-9\/%³]+)?\b', summary)
        key_data = ""
        if numbers:
            key_data = f"| Parameter | Extracted Metric |\n|---|---|\n| {term} | {', '.join(numbers[:4])} |"

        entities.append({
            "title": term,
            "name": term,
            "type": "Concept",
            "summary": summary,
            "source_location": "Extracted from document text",
            "key_data": key_data,
            "relationships": [],
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
