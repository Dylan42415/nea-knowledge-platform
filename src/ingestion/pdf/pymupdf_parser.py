"""
PyMuPDF Parser for PDF Documents.
"""
import logging
import fitz  # type: ignore
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

def extract_text(file_path: Path) -> Dict[str, Any]:
    """
    Extract text and metadata from a PDF using PyMuPDF.
    
    Args:
        file_path (Path): Path to the PDF file.
        
    Returns:
        dict: A dictionary containing metadata and list of pages with text.
    """
    result: Dict[str, Any] = {
        "metadata": {},
        "pages": []
    }
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return result

    try:
        doc = fitz.open(str(file_path))
    except Exception as e:
        logger.error(f"Failed to open PDF {file_path}: {e}")
        return result

    metadata = doc.metadata or {}
    result["metadata"] = {
        "title": metadata.get("title", ""),
        "author": metadata.get("author", ""),
        "creation_date": metadata.get("creationDate", ""),
        "page_count": len(doc)
    }

    first_heading_candidate = None

    for page_num in range(len(doc)):
        try:
            page = doc[page_num]
            text = page.get_text()
            
            # Simple heuristic for title if missing
            if page_num == 0 and not result["metadata"]["title"]:
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                if lines:
                    first_heading_candidate = lines[0]
            
            result["pages"].append({
                "page_num": page_num + 1,
                "text": text,
                "images": []
            })
        except Exception as e:
            logger.warning(f"Failed to extract text from page {page_num + 1} of {file_path}: {e}")
            
    if not result["metadata"]["title"] and first_heading_candidate:
        result["metadata"]["title"] = first_heading_candidate

    doc.close()
    return result
