"""
Unit tests for Vault RAG Chatbot engine and BM25 relevance ranker.
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
_current = Path(__file__).resolve()
for _p in [_current] + list(_current.parents):
    if (_p / "src").is_dir():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

from src.chat.vault_index import build_vault_index, rank_vault_notes, search_vault_context
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

def test_bm25_repetitive_text_saturation(tmp_path: Path):
    """Test that a concise exact match beats a long repetitive document with term frequency saturation."""
    vault_dir = tmp_path / "vault"
    concepts_dir = vault_dir / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    # Note A: Exact title match and concise content
    note_a = concepts_dir / "benzene.md"
    note_a.write_text("""---
title: Benzene
type: Concept
source_document: soe_report.pdf
source_location: p. 14
---
# Benzene
Average 2020 concentration was 0.28 ppb.
""", encoding="utf-8")

    # Note B: Long document repeating keyword many times
    note_b = concepts_dir / "generic_report.md"
    repetitive_text = "benzene " * 100 + "some general discussion " * 100
    note_b.write_text(f"""---
title: Generic Long Report
type: Dataset
---
# Generic Long Report
{repetitive_text}
""", encoding="utf-8")

    results = rank_vault_notes("benzene levels in 2020", vault_dir, top_k=2)
    assert len(results) == 2
    # Benzene.md must rank FIRST due to title boost and BM25 length normalization
    assert results[0][1]["title"] == "Benzene"
    assert results[0][0] >= results[1][0]

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

def test_generate_vault_response_fallback(tmp_path: Path, monkeypatch):
    """Test fallback response generation when Gemini is unavailable."""
    import src.chat.chat_engine as ce
    monkeypatch.setattr(ce, "_get_genai_client", lambda: None)

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
    assert "Top Match" in response
