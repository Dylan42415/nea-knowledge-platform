import os
import sys
import streamlit as st
import yaml
from pathlib import Path
from datetime import datetime

# Ensure project root is in sys.path
_current = Path(__file__).resolve()
for _p in [_current] + list(_current.parents):
    if (_p / "src").is_dir():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

from src.app.components.search_bar import render_search_bar
from src.app.components.note_card import render_note_card
from src.config import VAULT_ROOT

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                metadata = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return metadata or {}, body
            except Exception:
                pass
    return {}, content

def render_browse_page():
    """Renders the browse and search page."""
    st.title("📚 Browse Knowledge Base")
    
    query = render_search_bar()
    
    # First load all notes to dynamically compute available types and tags
    all_raw_notes = []
    available_tags = set()
    available_types = {"All"}
    
    vault_dir = Path(VAULT_ROOT)
    if vault_dir.exists():
        for filepath in vault_dir.rglob('*.md'):
            filename = filepath.name
            try:
                content = filepath.read_text(encoding="utf-8")
                metadata, body = parse_frontmatter(content)
                title = metadata.get("title", filename.replace(".md", ""))
                note_type = metadata.get("type", "Concept")
                tags = metadata.get("tags") or []
                if isinstance(tags, str):
                    tags = [tags]
                tags = [str(t) for t in tags if t]
                date = metadata.get("extraction_date") or metadata.get("date", datetime.now().strftime("%Y-%m-%d"))
                
                available_types.add(note_type.capitalize())
                for t in tags:
                    available_tags.add(t)

                all_raw_notes.append({
                    "title": title,
                    "type": note_type,
                    "tags": tags,
                    "preview": body[:150] + "..." if len(body) > 150 else body,
                    "date": str(date),
                    "body": body
                })
            except Exception:
                continue

    sorted_types = ["All"] + sorted([t for t in available_types if t != "All"])
    sorted_tags = sorted(available_tags)

    col1, col2 = st.columns([1, 2])
    with col1:
        type_filter = st.selectbox("Filter by Type", sorted_types)
    with col2:
        tag_filter = st.multiselect("Filter by Tags", sorted_tags)
        
    st.markdown("---")
    
    # Filter loaded notes
    notes = []
    for note in all_raw_notes:
        if type_filter != "All" and type_filter.lower() != note["type"].lower():
            continue
        if tag_filter and not any(t in note["tags"] for t in tag_filter):
            continue
        if query and query.lower() not in note["title"].lower() and query.lower() not in note["body"].lower():
            continue
        notes.append(note)
                
    if not notes:
        st.info("No notes found matching your criteria. Try adjusting filters or ingesting more data.")
    else:
        for note in notes:
            with st.container():
                render_note_card(
                    title=note["title"],
                    note_type=note["type"],
                    tags=note["tags"],
                    preview=note["preview"],
                    date=note["date"]
                )
                with st.expander("View Full Note"):
                    st.markdown(note["body"])

if __name__ == "__main__" or not __name__.startswith("src."):
    render_browse_page()
