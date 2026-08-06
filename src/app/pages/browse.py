import os
import streamlit as st
import yaml
from datetime import datetime
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
    
    col1, col2 = st.columns([1, 2])
    with col1:
        type_filter = st.selectbox(
            "Filter by Type",
            ["All", "Dataset", "Concept", "Location", "Organization"]
        )
    with col2:
        tag_filter = st.multiselect(
            "Filter by Tags",
            ["water", "air-quality", "waste-management", "policy", "sensor", "active"]
        )
        
    st.markdown("---")
    
    notes = []
    
    # Read notes from vault
    vault_dir = os.path.join(VAULT_ROOT, 'vault')
    if os.path.exists(vault_dir):
        for filename in os.listdir(vault_dir):
            if filename.endswith(".md"):
                filepath = os.path.join(vault_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                metadata, body = parse_frontmatter(content)
                title = metadata.get("title", filename.replace(".md", ""))
                note_type = metadata.get("type", "concept")
                tags = metadata.get("tags", [])
                date = metadata.get("date", datetime.now().strftime("%Y-%m-%d"))
                
                # Apply filters
                if type_filter != "All" and type_filter.lower() != note_type.lower():
                    continue
                if tag_filter and not any(t in tags for t in tag_filter):
                    continue
                if query and query.lower() not in title.lower() and query.lower() not in body.lower():
                    continue
                    
                notes.append({
                    "title": title,
                    "type": note_type,
                    "tags": tags,
                    "preview": body[:150] + "..." if len(body) > 150 else body,
                    "date": date,
                    "body": body
                })
                
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
