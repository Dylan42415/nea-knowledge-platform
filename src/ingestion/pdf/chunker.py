"""
Structure-aware Chunking Module.
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def chunk_document(parsed_doc: Dict[str, Any], max_chunk_size: int = 2000) -> List[Dict[str, Any]]:
    """
    Chunk a document based on section and heading boundaries.
    
    Args:
        parsed_doc (dict): Parsed document output from extract_with_layout.
        max_chunk_size (int): Maximum character length of a text chunk.
        
    Returns:
        list[dict]: List of chunks with type, content, and metadata.
    """
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0
    
    # 1. Process Tables
    for table in parsed_doc.get("tables", []):
        table_str = _format_table(table.get("data", []))
        chunks.append({
            "chunk_index": chunk_index,
            "chunk_type": "table",
            "heading": table.get("caption", "Table"),
            "content": f"{table.get('caption', '')}\n{table_str}"
        })
        chunk_index += 1
        
    # 2. Process Sections (Text)
    for section in parsed_doc.get("sections", []):
        heading = section.get("heading", "")
        content = section.get("content", "")
        
        if len(content) <= max_chunk_size:
            chunks.append({
                "chunk_index": chunk_index,
                "chunk_type": "text",
                "heading": heading,
                "content": content
            })
            chunk_index += 1
        else:
            paragraphs = content.split("\n\n")
            current_chunk_text = ""
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                    
                if len(current_chunk_text) + len(para) + 2 > max_chunk_size:
                    if current_chunk_text:
                        chunks.append({
                            "chunk_index": chunk_index,
                            "chunk_type": "text",
                            "heading": heading,
                            "content": current_chunk_text.strip()
                        })
                        chunk_index += 1
                        current_chunk_text = ""
                        
                    if len(para) > max_chunk_size:
                        for i in range(0, len(para), max_chunk_size):
                            chunks.append({
                                "chunk_index": chunk_index,
                                "chunk_type": "text",
                                "heading": heading,
                                "content": para[i:i+max_chunk_size]
                            })
                            chunk_index += 1
                    else:
                        current_chunk_text = para + "\n\n"
                else:
                    current_chunk_text += para + "\n\n"
                    
            if current_chunk_text.strip():
                chunks.append({
                    "chunk_index": chunk_index,
                    "chunk_type": "text",
                    "heading": heading,
                    "content": current_chunk_text.strip()
                })
                chunk_index += 1
                
    # 3. Process Pages (if sections is empty but pages is present)
    if not parsed_doc.get("sections") and parsed_doc.get("pages"):
        for page in parsed_doc.get("pages", []):
            text = page.get("text", "")
            page_num = page.get("page_num", 1)
            heading = f"Page {page_num}"
            if not text.strip():
                continue
            if len(text) <= max_chunk_size:
                chunks.append({
                    "chunk_index": chunk_index,
                    "chunk_type": "text",
                    "heading": heading,
                    "content": text
                })
                chunk_index += 1
            else:
                paragraphs = text.split("\n\n")
                current_chunk_text = ""
                for para in paragraphs:
                    para = para.strip()
                    if not para:
                        continue
                    if len(current_chunk_text) + len(para) + 2 > max_chunk_size:
                        if current_chunk_text:
                            chunks.append({
                                "chunk_index": chunk_index,
                                "chunk_type": "text",
                                "heading": heading,
                                "content": current_chunk_text.strip()
                            })
                            chunk_index += 1
                            current_chunk_text = ""
                        if len(para) > max_chunk_size:
                            for i in range(0, len(para), max_chunk_size):
                                chunks.append({
                                    "chunk_index": chunk_index,
                                    "chunk_type": "text",
                                    "heading": heading,
                                    "content": para[i:i+max_chunk_size]
                                })
                                chunk_index += 1
                        else:
                            current_chunk_text = para + "\n\n"
                    else:
                        current_chunk_text += para + "\n\n"
                if current_chunk_text.strip():
                    chunks.append({
                        "chunk_index": chunk_index,
                        "chunk_type": "text",
                        "heading": heading,
                        "content": current_chunk_text.strip()
                    })
                    chunk_index += 1
                
    return chunks

def _format_table(data: List[List[str]]) -> str:
    """Format 2D list into a simple string representation (markdown-like)."""
    if not data:
        return ""
    
    formatted = []
    for row in data:
        formatted.append(" | ".join(str(cell) for cell in row))
    
    return "\n".join(formatted)
