"""Tests for concept extractor."""

import pytest
from src.extraction.concept_extractor import extract_concepts_fallback

def test_fallback_extract_concepts():
    """Test the fallback environmental entity concept extraction."""
    text = "The Benzene levels and PM2.5 in Singapore are monitored by National Environment Agency."
    concepts = extract_concepts_fallback(text)
    
    assert isinstance(concepts, list)
    assert len(concepts) > 0
    names = [c["name"] for c in concepts]
    assert "Benzene" in names or "PM2.5" in names or "National Environment Agency" in names

def test_gold_extractor_hole_finder():
    """Verify that unanchored data produces knowledge_gaps and IDENTIFIES_GAP relationships."""
    from src.extraction.gold_extractor import _heuristic_gold_fallback
    payload = {
        "title": "Acrolein Ambient Study",
        "content": "Acrolein is an aldehyde emitted by incomplete combustion. No formal guidelines exist.",
        "source_document": "air_report.pdf",
        "source_location": "p. 5"
    }
    notes = _heuristic_gold_fallback(payload)
    assert len(notes) == 1
    note = notes[0]
    assert "knowledge_gaps" in note
    assert len(note["knowledge_gaps"]) > 0
    # Check that an IDENTIFIES_GAP predicate was created for missing authority
    rel_predicates = [r["predicate"] for r in note["relationships"]]
    assert "IDENTIFIES_GAP" in rel_predicates

def test_strict_live_raises_on_failure_preventing_silent_fallback(monkeypatch):
    """Verify that strict_live=True raises RuntimeError instead of masking failure with fallback."""
    from src.extraction.gold_extractor import extract_gold_notes
    
    # Mock client to None or mock generation failure
    monkeypatch.setattr("src.extraction.gold_extractor._get_genai_client", lambda: None)
    
    payload = {
        "title": "Strict Mode Verification",
        "content": "Testing zero silent fallback mandate under API failure.",
        "source_document": "test.pdf",
        "source_location": "p. 1"
    }
    with pytest.raises(RuntimeError, match="Gemini GenAI client not initialized"):
        extract_gold_notes(payload, strict_live=True)

def test_gold_extractor_provenance_and_dynamic_statutory_extraction():
    """Verify provenance tagging and dynamic regex extraction of unseen statutory entities and acronyms."""
    from src.extraction.gold_extractor import _heuristic_gold_fallback
    
    payload = {
        "title": "Marine Biofouling",
        "content": "Regulations administered by Maritime and Port Authority under Merchant Shipping Act. Standards benchmarked by IMO and ISO: 15 µg/m³ limit in 2024.",
        "source_document": "marine_circ.pdf",
        "source_location": "p. 12"
    }
    notes = _heuristic_gold_fallback(payload)
    assert len(notes) == 1
    note = notes[0]
    
    # Check provenance
    assert note["extraction_source"] == "heuristic_fallback"
    
    # Check dynamic entities extracted via regex rather than static lists
    targets = [r["target"] for r in note["relationships"]]
    assert any("Maritime and Port Authority" in t for t in targets)
    assert any("Merchant Shipping Act" in t for t in targets)
    assert "IMO" in targets or "ISO" in targets

