"""Tests for vault writer components."""

import pytest
from pathlib import Path
from src.vault_writer.note_generator import sanitize_filename
from src.vault_writer.linker import create_wikilinks

def test_sanitize_filename():
    """Test filename sanitization."""
    assert sanitize_filename("hello/world.txt") == "helloworld.txt"
    assert sanitize_filename("test:name") == "testname"
    assert sanitize_filename("valid_name-123.md") == "valid_name-123.md"


def test_linker_create_wikilink():
    """Test creation of wikilinks."""
    assert create_wikilinks(["Concept"]) == "[[Concept]]"
    assert create_wikilinks(["Another Concept"]) == "[[Another Concept]]"


def test_generate_note_knowledge_gaps():
    """Verify that generate_note renders Knowledge Gaps & Unresolved Blindspots."""
    from src.vault_writer.note_generator import generate_note
    note_data = {
        "title": "Acrolein",
        "summary": "Volatile pollutant.",
        "knowledge_gaps": [
            "Missing baseline threshold",
            "No historical sampling before 2020"
        ]
    }
    content = generate_note(note_data, "concept")
    assert "## Knowledge Gaps & Unresolved Blindspots" in content
    assert "⚠️ Missing baseline threshold" in content
    assert "knowledge_gaps:" in content
