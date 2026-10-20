"""Tests for PDF parsing components."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ingestion.pdf.classifier import classify_pdf
from src.ingestion.pdf.pymupdf_parser import extract_text
from src.ingestion.pdf.chunker import chunk_document

def test_classify_pdf_missing_file():
    """Test classification of a non-existent PDF."""
    with pytest.raises(FileNotFoundError):
        classify_pdf(Path("non_existent_file.pdf"))

import fitz

def test_pymupdf_extract_text(tmp_path):
    """Test real text extraction using PyMuPDF on an actual generated PDF."""
    pdf_path = tmp_path / "sample_real.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Real PDF test content for NEA extraction.")
    doc.save(str(pdf_path))
    doc.close()

    result = extract_text(pdf_path)
    
    assert "pages" in result
    assert len(result["pages"]) == 1
    assert "Real PDF test content" in result["pages"][0]["text"]

def test_chunker_respects_max_size():
    """Test chunker splits text correctly based on max chunk size."""
    data = {"sections": [{"heading": "h1", "content": "This is a test string that is long"}]}
    chunks = chunk_document(data, max_chunk_size=20)
    
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["content"]) <= 20
