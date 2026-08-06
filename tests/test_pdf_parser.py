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

@patch("src.ingestion.pdf.pymupdf_parser.Path.exists")
@patch("src.ingestion.pdf.pymupdf_parser.fitz")
def test_pymupdf_extract_text(mock_fitz, mock_exists):
    """Test text extraction using PyMuPDF."""
    mock_exists.return_value = True
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Test content"
    mock_doc.__iter__.return_value = [mock_page]
    mock_doc.__len__.return_value = 1
    mock_doc.__getitem__.return_value = mock_page
    mock_fitz.open.return_value = mock_doc

    result = extract_text(Path("dummy.pdf"))
    
    assert "pages" in result
    assert len(result["pages"]) == 1
    assert result["pages"][0]["text"] == "Test content"

def test_chunker_respects_max_size():
    """Test chunker splits text correctly based on max chunk size."""
    data = {"sections": [{"heading": "h1", "content": "This is a test string that is long"}]}
    chunks = chunk_document(data, max_chunk_size=20)
    
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 20
