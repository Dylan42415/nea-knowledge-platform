"""
PDF Classification Module.
"""
import logging
import fitz  # type: ignore # PyMuPDF
from pathlib import Path

logger = logging.getLogger(__name__)

def classify_pdf(file_path: Path) -> str:
    """
    Classify a PDF as 'text' (native) or 'scanned' based on extractable text content.
    
    Args:
        file_path (Path): Path to the PDF file.
        
    Returns:
        str: 'text' if >80% of pages contain text, otherwise 'scanned'.
    """
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        doc = fitz.open(str(file_path))
    except Exception as e:
        logger.error(f"Failed to open PDF {file_path}: {e}")
        raise
        
    num_pages = len(doc)
    if num_pages == 0:
        return 'scanned'

    pages_with_text = 0
    for page_num in range(num_pages):
        page = doc[page_num]
        text = page.get_text().strip()
        if len(text) > 50:  # arbitrary threshold for "meaningful" text
            pages_with_text += 1

    doc.close()
    
    text_ratio = pages_with_text / num_pages
    if text_ratio > 0.8:
        return 'text'
    return 'scanned'
