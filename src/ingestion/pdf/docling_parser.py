"""
Layout-aware extraction using Docling.
"""
import logging
from pathlib import Path
from typing import Dict, Any
from .pymupdf_parser import extract_text as pymupdf_extract

logger = logging.getLogger(__name__)

try:
    from docling.document_converter import DocumentConverter  # type: ignore
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    logger.warning("docling is not installed. Falling back to PyMuPDF parser.")

def extract_with_layout(file_path: Path) -> Dict[str, Any]:
    """
    Extract structured content (sections, tables) using Docling, falling back to PyMuPDF.
    
    Args:
        file_path (Path): Path to the PDF file.
        
    Returns:
        dict: Structured output with sections, tables, and metadata.
    """
    if not DOCLING_AVAILABLE:
        logger.warning(f"Using fallback PyMuPDF parser for {file_path}")
        return _fallback_extraction(file_path)
        
    try:
        converter = DocumentConverter()
        doc = converter.convert(str(file_path)).document
        
        result: Dict[str, Any] = {
            "metadata": {},
            "sections": [],
            "tables": []
        }
        
        current_heading = "Unknown Section"
        current_level = 1
        current_content = []
        
        for item in doc.texts:
            if item.label == "title":
                result["metadata"]["title"] = item.text
            elif str(item.label).startswith("heading"):
                if current_content:
                    result["sections"].append({
                        "heading": current_heading,
                        "level": current_level,
                        "content": "\n".join(current_content)
                    })
                    current_content = []
                
                current_heading = item.text
                try:
                    current_level = int(str(item.label).split("_")[1]) if "_" in str(item.label) else 1
                except:
                    current_level = 1
            else:
                current_content.append(item.text)
                
        if current_content:
            result["sections"].append({
                "heading": current_heading,
                "level": current_level,
                "content": "\n".join(current_content)
            })
            
        for table in doc.tables:
            caption = table.caption.text if getattr(table, 'caption', None) else "Table"
            
            table_data = []
            if hasattr(table, 'export_to_dataframe'):
                df = table.export_to_dataframe()
                table_data = [df.columns.tolist()] + df.values.tolist()
            
            result["tables"].append({
                "caption": caption,
                "data": table_data
            })
            
        return result
        
    except Exception as e:
        logger.error(f"Docling extraction failed for {file_path}: {e}")
        logger.warning(f"Falling back to PyMuPDF parser for {file_path}")
        return _fallback_extraction(file_path)

def _fallback_extraction(file_path: Path) -> Dict[str, Any]:
    """Fallback method using PyMuPDF when Docling is unavailable."""
    basic_data = pymupdf_extract(file_path)
    
    sections = []
    current_content = []
    
    for page in basic_data.get("pages", []):
        current_content.append(page.get("text", ""))
        
    if current_content:
        sections.append({
            "heading": "Document Content",
            "level": 1,
            "content": "\n".join(current_content)
        })
        
    return {
        "metadata": basic_data.get("metadata", {}),
        "sections": sections,
        "tables": []
    }
