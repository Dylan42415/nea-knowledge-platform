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
