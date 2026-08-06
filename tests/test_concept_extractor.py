"""Tests for concept extractor."""

import pytest
from src.extraction.concept_extractor import extract_concepts_fallback

def test_fallback_extract_concepts():
    """Test the fallback regex concept extraction."""
    text = "The Marina Bay and Sentosa are key locations in Singapore."
    concepts = extract_concepts_fallback(text)
    
    assert isinstance(concepts, list)
    assert len(concepts) > 0
    # Assuming the fallback extracts capitalized words/phrases
    # Depending on implementation it might return dictionaries with 'name' or just strings.
    # Let's adjust to checking the output generally.
    if concepts and isinstance(concepts[0], dict):
        assert any("Marina Bay" in c.get("name", "") or "Sentosa" in c.get("name", "") or "Singapore" in c.get("name", "") for c in concepts)
    else:
        assert any("Marina Bay" in c or "Sentosa" in c or "Singapore" in c for c in concepts)
