"""
Unit tests for Vault RAG Chatbot engine and context retriever.
"""
from pathlib import Path
from src.chat.vault_index import build_vault_index, search_vault_context
from src.chat.chat_engine import generate_vault_response

def test_build_vault_index(tmp_path: Path):
    """Test building index over a temporary vault directory."""
    vault_dir = tmp_path / "vault"
    datasets_dir = vault_dir / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)

    note = datasets_dir / "test_report.md"
    note.write_text("""---
title: Test Air Quality Report
type: Dataset
source_document: test_report.pdf
source_location: p. 1
extraction_date: '2026-08-06'
tags: [air-quality]
---

# Test Air Quality Report

## Summary
Test report on ambient air quality parameters.
""", encoding="utf-8")

    index = build_vault_index(vault_dir)
    assert len(index) == 1
    assert index[0]["title"] == "Test Air Quality Report"
    assert index[0]["source_document"] == "test_report.pdf"

def test_search_vault_context(tmp_path: Path):
    """Test searching context across vault notes."""
    vault_dir = tmp_path / "vault"
    concepts_dir = vault_dir / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    note = concepts_dir / "benzene.md"
    note.write_text("""---
title: Benzene
type: Concept
source_document: soe_report.pdf
source_location: p. 14
---

# Benzene

## Summary
Average 2020 concentration was 0.28 ppb.
""", encoding="utf-8")

    context = search_vault_context("Benzene 2020 concentration", vault_dir)
    assert "[[Benzene]]" in context
    assert "0.28 ppb" in context

def test_generate_vault_response_fallback(tmp_path: Path):
    """Test fallback response generation when Gemini is unavailable."""
    vault_dir = tmp_path / "vault"
    concepts_dir = vault_dir / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    note = concepts_dir / "benzene.md"
    note.write_text("""---
title: Benzene
type: Concept
source_document: soe_report.pdf
source_location: p. 14
---

# Benzene
Average 2020 concentration was 0.28 ppb.
""", encoding="utf-8")

    messages = [{"role": "user", "content": "What is Benzene level?"}]
    response = generate_vault_response(messages, vault_root=vault_dir)
    assert "Benzene" in response
