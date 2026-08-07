"""
Vault Context Indexer with BM25 Length-Normalized & Title-Boosted Ranking Engine for Obsidian Vault.
"""
import re
import math
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple

STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is", "are", 
    "was", "were", "be", "been", "being", "what", "where", "which", "who", "whom", 
    "this", "that", "these", "those", "how", "why", "does", "do", "did", "have", 
    "has", "had", "its", "it", "they", "them", "their", "from", "by", "with", "about"
}

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

    aliases = meta.get("aliases", [])
    if isinstance(aliases, str):
        aliases = [aliases]

    return {
        "filepath": str(filepath),
        "filename": filepath.name,
        "title": meta.get("title") or title,
        "aliases": aliases,
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

def rank_vault_notes(query: str, vault_root: Path, top_k: int = 5) -> List[Tuple[float, Dict[str, Any]]]:
    """
    High-precision ranking engine for vault notes using BM25 term frequency saturation (k1=1.2, b=0.75),
    document length normalization, and exact entity title boosting (+100).

    Returns:
        List of (confidence_score, note_dict) tuples sorted descending by score.
    """
    notes = build_vault_index(vault_root)
    if not notes:
        return []

    # Extract non-stop words
    raw_terms = re.findall(r'\w+', query.lower())
    query_terms = [t for t in raw_terms if len(t) > 1 and t not in STOP_WORDS]
    if not query_terms:
        query_terms = raw_terms

    # Calculate corpus document lengths and average length
    doc_lengths = {id(n): len(n['body'].split()) for n in notes}
    avgdl = sum(doc_lengths.values()) / len(notes) if notes else 1.0

    # Calculate Inverse Document Frequency (IDF) for query terms
    N = len(notes)
    idf = {}
    for term in query_terms:
        doc_count = sum(1 for n in notes if term in f"{n['title']} {' '.join(n.get('aliases', []))} {n['body']}".lower())
        idf[term] = math.log((N - doc_count + 0.5) / (doc_count + 0.5) + 1.0)

    # BM25 Parameters
    k1 = 1.2
    b = 0.75

    scored_notes = []
    clean_query_phrase = " ".join(query_terms)

    for note in notes:
        title_lower = note['title'].lower()
        body_lower = note['body'].lower()
        aliases_lower = [a.lower() for a in note.get("aliases", [])]
        doc_len = doc_lengths[id(note)]

        score = 0.0

        # 1. Exact Title / Alias Match Boost
        if title_lower == clean_query_phrase or clean_query_phrase in aliases_lower:
            score += 100.0
        elif clean_query_phrase in title_lower or any(clean_query_phrase in a for a in aliases_lower):
            score += 60.0

        # 2. BM25 Saturated Term Frequency Score with Length Normalization
        for term in query_terms:
            term_idf = idf.get(term, 1.0)
            
            # Title & Alias match boost per query term & domain shortcuts
            alias_match = any(term == a or term in a for a in aliases_lower)
            if term in title_lower or alias_match or (term == "psi" and "pollutant" in title_lower) or (term == "pm25" and "pm2.5" in title_lower):
                score += 40.0 * term_idf
            
            # Count raw term frequency in body
            tf = len(re.findall(r'\b' + re.escape(term) + r'\b', body_lower))
            if tf > 0:
                # BM25 saturation formula: prevents long repetitive text from inflating score
                denom = tf + k1 * (1.0 - b + b * (doc_len / avgdl))
                bm25_tf = (tf * (k1 + 1.0)) / denom
                score += bm25_tf * term_idf

        # 3. Exact Phrase Match Boost
        if len(query_terms) > 1 and clean_query_phrase in body_lower:
            score += 25.0

        if score > 0:
            scored_notes.append((score, note))

    scored_notes.sort(key=lambda x: x[0], reverse=True)
    if not scored_notes:
        return []

    max_score = scored_notes[0][0]
    results = []
    for raw_score, note in scored_notes[:top_k]:
        confidence = round(min(0.99, max(0.50, raw_score / (max_score + 1.0))), 2)
        results.append((confidence, note))

    return results

def search_vault_context(query: str, vault_root: Path, max_notes: int = 5) -> str:
    """
    Perform high-precision BM25 relevance ranking over vault notes and build structured 
    context string for LLM (Top 3-5 notes maximum).
    """
    ranked_results = rank_vault_notes(query, vault_root, top_k=max_notes)
    if not ranked_results:
        return "No relevant notes found in vault."

    context_blocks = []
    for conf, note in ranked_results:
        block = f"--- NOTE: [[{note['title']}]] (Confidence: {conf}) ---\n"
        block += f"Type: {note['type']}\n"
        if note['source_document']:
            block += f"Source Document: {note['source_document']}\n"
        if note['source_location']:
            block += f"Source Location: {note['source_location']}\n"
        block += f"\nContent:\n{note['body']}\n"
        context_blocks.append(block)

    return "\n".join(context_blocks)
