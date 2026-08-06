"""
Vault Context Indexer for full Obsidian Vault RAG retrieval.
"""
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any

def parse_note(filepath: Path) -> Dict[str, Any]:
    """Parse a Markdown vault note into a structured dictionary."""
    content = filepath.read_text(encoding="utf-8")
    title = filepath.stem.replace("_", " ").title()
    meta = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
            except Exception:
                pass

    return {
        "filepath": str(filepath),
        "filename": filepath.name,
        "title": meta.get("title") or title,
        "type": meta.get("type") or filepath.parent.name.rstrip("s").capitalize(),
        "source_document": meta.get("source_document") or meta.get("source_file", ""),
        "source_location": meta.get("source_location", ""),
        "extraction_date": meta.get("extraction_date", ""),
        "tags": meta.get("tags", []),
        "body": body,
        "raw_content": content
    }

def build_vault_index(vault_root: Path) -> List[Dict[str, Any]]:
    """Scan all markdown files in vault directory."""
    if not vault_root.exists():
        return []

    notes = []
    for filepath in vault_root.rglob("*.md"):
        if filepath.name.startswith(".") or filepath.parent.name == "_templates":
            continue
        try:
            note = parse_note(filepath)
            notes.append(note)
        except Exception:
            continue

    return notes

def search_vault_context(query: str, vault_root: Path, max_notes: int = 15) -> str:
    """
    Perform relevance scoring over vault notes and build structured context string for LLM.
    """
    notes = build_vault_index(vault_root)
    if not notes:
        return "No notes found in vault."

    query_terms = set(re.findall(r'\w+', query.lower()))

    # Score notes based on query match frequency in title, body, and tags
    scored_notes = []
    for note in notes:
        score = 0
        text = f"{note['title']} {note['type']} {' '.join(note['tags'])} {note['body']}".lower()
        title_lower = note['title'].lower()

        for term in query_terms:
            if len(term) < 2:
                continue
            if term in title_lower:
                score += 10
            matches = len(re.findall(r'\b' + re.escape(term) + r'\b', text))
            score += matches

        scored_notes.append((score, note))

    scored_notes.sort(key=lambda x: x[0], reverse=True)

    # If top score is 0 (broad query), return top recent notes
    selected_notes = [n for s, n in scored_notes[:max_notes]] if scored_notes[0][0] > 0 else notes[:max_notes]

    context_blocks = []
    for note in selected_notes:
        block = f"--- NOTE: [[{note['title']}]] ---\n"
        block += f"Type: {note['type']}\n"
        if note['source_document']:
            block += f"Source Document: {note['source_document']}\n"
        if note['source_location']:
            block += f"Source Location: {note['source_location']}\n"
        block += f"\nContent:\n{note['body']}\n"
        context_blocks.append(block)

    return "\n".join(context_blocks)
