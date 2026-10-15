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

    raw_aliases = meta.get("aliases")
    if isinstance(raw_aliases, str):
        aliases = [raw_aliases]
    elif isinstance(raw_aliases, list):
        aliases = [str(a) for a in raw_aliases if a is not None]
    else:
        aliases = []

    return {
        "filepath": str(filepath),
        "filename": filepath.name,
        "title": meta.get("title") or title,
        "aliases": aliases,
        "type": meta.get("type") or filepath.parent.name.rstrip("s").capitalize(),
        "source_document": meta.get("source_document") or meta.get("source_file", ""),
        "source_location": meta.get("source_location", ""),
        "extraction_date": meta.get("extraction_date", ""),
        "tags": meta.get("tags") or [],
        "body": body,
        "raw_content": content
    }

try:
    import streamlit as st
    _vault_cache = st.cache_data(ttl=30)
except Exception:
    def _vault_cache(f):
        return f

@_vault_cache
def _get_cached_vault_notes(vault_root_str: str) -> List[Dict[str, Any]]:
    """Cached disk scanner for vault notes."""
    vault_root = Path(vault_root_str)
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

def build_vault_index(vault_root: Path) -> List[Dict[str, Any]]:
    """Scan all markdown files in vault directory using cached disk scanner."""
    return _get_cached_vault_notes(str(vault_root))

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
            
            # Title & Alias match boost per query term (dynamic from frontmatter aliases)
            alias_match = any(term == a or term in a for a in aliases_lower)
            if term in title_lower or alias_match:
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

    results = []
    for raw_score, note in scored_notes[:top_k]:
        # Compute smooth monotonic confidence score from 0.00 to 1.00
        if raw_score <= 0:
            conf = 0.00
        elif raw_score >= 120.0:
            conf = 0.98
        else:
            conf = 0.45 + 0.52 * (1.0 - math.exp(-raw_score / 40.0))
        
        confidence = round(min(1.00, max(0.00, conf)), 2)
        results.append((confidence, note))

    return results


def is_stub_note(note: Dict[str, Any]) -> bool:
    """
    Check if a note is an empty stub or auto-generated placeholder.
    Filters out notes that have no substantial body text, preventing them from
    crowding out data-rich target notes in the LLM context window.
    """
    body = str(note.get("body") or "").strip()
    # Strip markdown headers and wikilink lines
    clean_body = re.sub(r'^#+\s+.*$', '', body, flags=re.MULTILINE).strip()
    clean_body = re.sub(r'^-\s+Linked from\s+\[\[.*?\]\].*$', '', clean_body, flags=re.MULTILINE).strip()
    clean_body = re.sub(r'\[\[.*?\]\]', '', clean_body).strip()
    
    # Check for markdown table indicators (e.g. |---| or |:---:|)
    has_table = bool(re.search(r'\|(?:\s*[:-]+[-| :]*)\|', body))
    
    # If the clean body text is less than 35 characters and contains no markdown table
    if len(clean_body) < 35 and not has_table:
        return True
    return False

def extract_wikilinks_from_note(note: Dict[str, Any]) -> List[str]:
    """Extract clean target titles from [[Wikilinks]] in a note's raw content."""
    raw = str(note.get("raw_content") or "")
    matches = re.findall(r'\[\[(.*?)\]\]', raw)
    targets = []
    for m in matches:
        # Strip alias display text e.g. [[Target#Heading|Display]] -> Target#Heading
        target = m.split('|')[0].strip()
        # Strip section anchors / block links e.g. Target#Heading -> Target
        target = target.split('#')[0].strip()
        # Strip folder paths if prefixed e.g. concepts/Target -> Target
        target = target.split('/')[-1].strip()
        if target:
            targets.append(target)
    return targets

def expand_graph_neighborhood(
    query: str, 
    vault_root: Path, 
    top_seeds: int = 3, 
    max_depth: int = 2, 
    max_total_notes: int = 6
) -> List[Dict[str, Any]]:
    """
    Programmatic Graph-RAG neighborhood expansion.
    1. Identifies top seed notes using BM25 relevance & exact title boosting.
    2. Expands 1-hop outgoing [[Wikilinks]] and incoming backlinks (canonicalized by aliases).
    3. Traverses 2-hop edges to reach leaf notes even when the query lacks leaf keywords.
    4. Filters out empty stub notes from consuming context slots.

    Returns:
        List of expanded note dicts containing {'note', 'hop', 'path', 'confidence', 'relation'}.
    """
    all_notes = build_vault_index(vault_root)
    if not all_notes:
        return []

    # Build canonical lookup indices
    lookup: Dict[str, Dict[str, Any]] = {}
    for n in all_notes:
        lookup[n["title"].lower()] = n
        lookup[n["filename"].lower()] = n
        lookup[Path(n["filename"]).stem.lower()] = n
        for alias in (n.get("aliases") or []):
            lookup[str(alias).lower()] = n

    # Build bidirectional graph links
    forward_links: Dict[str, List[str]] = {}
    backlinks: Dict[str, List[Dict[str, Any]]] = {}

    for n in all_notes:
        n_title = n["title"]
        links = extract_wikilinks_from_note(n)
        forward_links[n_title.lower()] = links
        for l in links:
            target_key = l.lower()
            if target_key not in backlinks:
                backlinks[target_key] = []
            backlinks[target_key].append(n)

            # Canonicalize: If target_key maps to an alias or filename, also index under target's canonical title
            resolved_target = lookup.get(target_key)
            if resolved_target:
                canon_key = resolved_target["title"].lower()
                if canon_key != target_key:
                    if canon_key not in backlinks:
                        backlinks[canon_key] = []
                    if n not in backlinks[canon_key]:
                        backlinks[canon_key].append(n)

    # Step 1: Retrieve top seed notes via BM25 + Title Boost
    ranked_seeds = rank_vault_notes(query, vault_root, top_k=top_seeds)
    if not ranked_seeds:
        return []

    # Filter out weak coincidence seeds if a dominant primary seed exists
    top_conf = ranked_seeds[0][0]
    filtered_seeds = []
    for conf, seed in ranked_seeds:
        if conf >= 0.55 or conf >= top_conf * 0.70 or len(filtered_seeds) == 0:
            filtered_seeds.append((conf, seed))

    visited_keys = set()
    collected: List[Dict[str, Any]] = []
    hop1_candidates: List[Tuple[Dict[str, Any], List[str], float, str]] = []

    # Collect non-stub seeds
    for conf, seed in filtered_seeds:
        key = seed["title"].lower()
        if key not in visited_keys:
            visited_keys.add(key)
            if not is_stub_note(seed):
                collected.append({
                    "note": seed,
                    "hop": 0,
                    "path": [seed["title"]],
                    "confidence": conf,
                    "relation": "Seed Match (BM25 + Title Boost)"
                })

            if max_depth <= 0:
                continue

            # Prepare 1-hop outgoing and incoming connections from seed
            # 1. Outgoing wikilinks
            for target_title in forward_links.get(key, []):
                t_key = target_title.lower()
                target_note = lookup.get(t_key)
                if target_note and target_note["title"].lower() != key:
                    hop1_candidates.append((
                        target_note, 
                        [seed["title"], target_note["title"]], 
                        round(conf * 0.85, 2),
                        f"Linked from [[{seed['title']}]]"
                    ))

            # 2. Incoming backlinks
            for b_note in backlinks.get(key, []):
                b_key = b_note["title"].lower()
                if b_key != key:
                    hop1_candidates.append((
                        b_note,
                        [seed["title"], b_note["title"]],
                        round(conf * 0.80, 2),
                        f"Backlinked from [[{b_note['title']}]]"
                    ))

    if max_depth <= 0:
        return collected

    # Step 2: 1-Hop Expansion
    hop2_candidates: List[Tuple[Dict[str, Any], List[str], float, str]] = []
    for cand_note, path, cand_conf, rel_desc in hop1_candidates:
        c_key = cand_note["title"].lower()
        if c_key not in visited_keys:
            visited_keys.add(c_key)
            if not is_stub_note(cand_note) and len(collected) < max_total_notes:
                collected.append({
                    "note": cand_note,
                    "hop": 1,
                    "path": path,
                    "confidence": cand_conf,
                    "relation": rel_desc
                })

            # Queue 2-hop traversal even if 1-hop was a structural bridge
            if max_depth >= 2:
                for target_2 in forward_links.get(c_key, []):
                    t2_key = target_2.lower()
                    target_note_2 = lookup.get(t2_key)
                    if target_note_2 and target_note_2["title"].lower() not in visited_keys:
                        root_title = path[0]
                        pred_title = cand_note["title"]
                        hop2_candidates.append((
                            target_note_2,
                            path + [target_note_2["title"]],
                            round(cand_conf * 0.75, 2),
                            f"2-Hop Leaf via [[{root_title}]] → [[{pred_title}]]"
                        ))

    # Step 3: 2-Hop Expansion (Reaching Leaf Nodes)
    if max_depth >= 2:
        for cand2_note, path2, cand2_conf, rel2_desc in hop2_candidates:
            if len(collected) >= max_total_notes:
                break
            c2_key = cand2_note["title"].lower()
            if c2_key not in visited_keys:
                visited_keys.add(c2_key)
                if not is_stub_note(cand2_note):
                    collected.append({
                        "note": cand2_note,
                        "hop": 2,
                        "path": path2,
                        "confidence": cand2_conf,
                        "relation": rel2_desc
                    })

    return collected


def search_vault_context(
    query: str, 
    vault_root: Path, 
    max_notes: int = 6, 
    max_depth: int = 2,
    top_seeds: int = 2
) -> str:
    """
    Perform Graph-RAG retrieval: Seed node identification via BM25 + Title Boosting,
    followed by programmatic 1-hop and 2-hop neighborhood expansion over [[Wikilinks]]
    and backlinks, filtering out empty stubs.
    """
    expanded_results = expand_graph_neighborhood(
        query=query, 
        vault_root=vault_root, 
        top_seeds=top_seeds, 
        max_depth=max_depth, 
        max_total_notes=max_notes
    )
    if not expanded_results:
        return "No relevant notes found in vault."

    context_blocks = []
    for item in expanded_results:
        note = item["note"]
        hop = item["hop"]
        conf = item["confidence"]
        relation = item["relation"]
        path_str = " → ".join([f"[[{p}]]" for p in item["path"]])

        if hop == 0:
            header = f"--- SEED NOTE (Hop 0): [[{note['title']}]] (Relevance Confidence: {conf:.2f}) ---"
        elif hop == 1:
            header = f"--- GRAPH NEIGHBOR (Hop 1): [[{note['title']}]] ({relation}) ---"
        else:
            header = f"--- GRAPH LEAF (Hop 2): [[{note['title']}]] ({relation}) ---"

        block = f"{header}\n"
        block += f"Type: {note['type']}\n"
        block += f"Graph Provenance Path: {path_str}\n"
        if note['source_document']:
            block += f"Source Document: {note['source_document']}\n"
        if note['source_location']:
            block += f"Source Location: {note['source_location']}\n"
        block += f"\nContent:\n{note['body']}\n"
        context_blocks.append(block)

    return "\n".join(context_blocks)

