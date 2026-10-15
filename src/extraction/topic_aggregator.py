"""
Topic and Section Aggregator for document-level knowledge extraction.
Groups document text, tables, figures, and page citations into complete section payloads.
"""
import re
from typing import List, Dict, Any

def aggregate_topics_from_document(parsed_doc: Dict[str, Any], doc_filename: str) -> List[Dict[str, Any]]:
    """
    Aggregate parsed document into topic-based section payloads.

    Args:
        parsed_doc: Dictionary from PyMuPDF or Docling parser containing pages, sections, or tables.
        doc_filename: Source document filename (e.g. 'soe_report.pdf').

    Returns:
        List of topic payloads [{'title': ..., 'type': ..., 'text': ..., 'source_location': ..., 'tables': ...}]
    """
    sections = parsed_doc.get("sections", [])
    pages = parsed_doc.get("pages", [])

    topic_payloads = []

    # If layout-aware sections exist (Docling parser)
    if sections:
        current_topic = None
        for sec in sections:
            heading = sec.get("heading", "").strip()
            content = sec.get("content", "").strip()
            level = sec.get("level", 1)

            if heading and len(heading) > 2 and level <= 2:
                if current_topic and current_topic.get("content"):
                    topic_payloads.append(current_topic)
                current_topic = {
                    "title": heading,
                    "content": f"# {heading}\n\n{content}",
                    "source_document": doc_filename,
                    "source_location": f"section '{heading}'"
                }
            elif current_topic:
                current_topic["content"] += f"\n\n{content}"

        if current_topic and current_topic.get("content"):
            topic_payloads.append(current_topic)

    # Fallback to page-based topic aggregation (PyMuPDF parser)
    if not topic_payloads and pages:
        # Group pages into ~4-page topical windows to preserve tables, trends, and cross-references
        window_size = 4
        for i in range(0, len(pages), window_size):
            window_pages = pages[i:i + window_size]
            start_page = window_pages[0].get("page_num", i + 1)
            end_page = window_pages[-1].get("page_num", i + len(window_pages))
            
            combined_text = "\n\n".join([p.get("text", "") for p in window_pages if p.get("text")])
            if not combined_text.strip():
                continue

            page_loc = f"pp. {start_page}-{end_page}" if start_page != end_page else f"p. {start_page}"
            
            # Detect major heading/topic in window
            first_line = combined_text.strip().split("\n")[0][:80]
            title = first_line.strip("# ").strip() if first_line else f"Topic Section {start_page}"

            topic_payloads.append({
                "title": title,
                "content": combined_text,
                "source_document": doc_filename,
                "source_location": page_loc
            })

    return topic_payloads
