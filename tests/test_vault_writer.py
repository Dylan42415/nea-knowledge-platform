"""Tests for vault writer components."""

import pytest
from pathlib import Path
from src.vault_writer.note_generator import sanitize_filename
from src.vault_writer.linker import create_wikilinks

def test_sanitize_filename():
    """Test filename sanitization."""
    assert sanitize_filename("hello/world.txt") == "helloworldtxt"
    assert sanitize_filename("test:name") == "testname"
    assert sanitize_filename("valid_name-123.md") == "valid_name_123md"

def test_linker_create_wikilink():
    """Test creation of wikilinks."""
    assert create_wikilinks(["Concept"]) == "[[Concept]]"
    assert create_wikilinks(["Another Concept"]) == "[[Another Concept]]"
