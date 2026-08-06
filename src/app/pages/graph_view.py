import os
import sys
import re
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import yaml
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import VAULT_ROOT
from src.vault_writer.note_generator import sanitize_filename

def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content."""
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                return yaml.safe_load(parts[1]) or {}
            except Exception:
                pass
    return {}

def render_graph_page():
    """Renders the knowledge graph visualization."""
    st.title("🕸️ Knowledge Graph")
    
    vault_dir = Path(VAULT_ROOT)
    if not vault_dir.exists() or not list(vault_dir.rglob('*.md')):
        st.info("Vault is empty. Please ingest some data to view the knowledge graph.")
        return
        
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Controls")
        node_type = st.selectbox(
            "Node Type",
            ["All", "Dataset", "Concept", "Location", "Organization"]
        )
        search_node = st.text_input("Search Node", "")
        
    type_colors = {
        "dataset": "#3b82f6",     # Blue
        "concept": "#22c55e",     # Green
        "location": "#f97316",    # Orange
        "organization": "#a855f7",# Purple
        "unknown": "#64748b"      # Gray
    }
    
    wikilink_pattern = re.compile(r'\[\[(.*?)\]\]')
    
    # Pass 1: Discover all notes and build title/alias -> node_ids mapping
    note_info = []
    title_to_ids: dict[str, list[str]] = {}
    
    def _add_mapping(key: str, val: str):
        if not key:
            return
        if key not in title_to_ids:
            title_to_ids[key] = []
        if val not in title_to_ids[key]:
            title_to_ids[key].append(val)
    
    for filepath in vault_dir.rglob("*.md"):
        filename = filepath.name
        safe_stem = filepath.stem
        
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            continue
            
        metadata = parse_frontmatter(content)
        title = metadata.get("title", safe_stem)
        ntype = metadata.get("type", filepath.parent.name.rstrip("s")).lower()
        
        # Unique node ID includes type/category prefix to prevent collisions
        node_id = f"{ntype}/{safe_stem}"
        
        _add_mapping(node_id, node_id)
        _add_mapping(safe_stem, node_id)
        _add_mapping(safe_stem.lower(), node_id)
        _add_mapping(title, node_id)
        _add_mapping(title.lower(), node_id)
        _add_mapping(sanitize_filename(title), node_id)
        
        note_info.append({
            "id": node_id,
            "title": title,
            "type": ntype,
            "content": content
        })
        
    nodes = []
    edges = []
    node_ids = set()
    node_labels = {}
    
    # Pass 2: Create nodes
    for note in note_info:
        ntype = note["type"]
        title = note["title"]
        node_id = note["id"]
        
        if node_type != "All" and ntype != node_type.lower():
            continue
            
        if search_node and search_node.lower() not in title.lower():
            continue
            
        node_ids.add(node_id)
        node_labels[node_id] = title
        
        nodes.append(Node(
            id=node_id,
            label=title,
            size=25,
            color=type_colors.get(ntype, type_colors["unknown"]),
            title=f"{ntype.capitalize()}: {title}"
        ))
        
    # Pass 3: Create edges using title_to_ids resolution
    for note in note_info:
        source_id = note["id"]
        if source_id not in node_ids:
            continue
            
        links = wikilink_pattern.findall(note["content"])
        for link in links:
            raw_target = link.split('|')[0].strip()
            target_ids = (
                title_to_ids.get(raw_target)
                or title_to_ids.get(raw_target.lower())
                or title_to_ids.get(sanitize_filename(raw_target))
            )
            
            if target_ids:
                for target_id in target_ids:
                    source_stem = source_id.split('/')[-1]
                    target_stem = target_id.split('/')[-1]
                    if target_id != source_id and source_stem != target_stem and target_id in node_ids:
                        edges.append(Edge(
                            source=source_id,
                            target=target_id,
                            color="#475569"
                        ))
            else:
                fallback_id = sanitize_filename(raw_target)
                source_stem = source_id.split('/')[-1]
                target_stem = fallback_id.split('/')[-1]
                if fallback_id != source_id and source_stem != target_stem:
                    edges.append(Edge(
                        source=source_id,
                        target=fallback_id,
                        color="#475569"
                    ))
            
    # Pass 4: Create missing nodes if a link truly has no corresponding file
    for edge in edges:
        if edge.target not in node_ids:
            display_label = edge.target.split("/")[-1].replace("_", " ").title()
            nodes.append(Node(
                id=edge.target,
                label=display_label,
                size=15,
                color=type_colors["unknown"],
                title=f"Unknown Node: {display_label}"
            ))
            node_ids.add(edge.target)
            
    with col2:
        config = Config(
            width=800,
            height=600,
            directed=True,
            physics=True,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#0ea5e9",
            collapsible=False,
            node={'labelProperty': 'label'},
            link={'labelProperty': 'label', 'renderLabel': False}
        )
        
        return_value = agraph(nodes=nodes, edges=edges, config=config)
        
        if return_value:
            st.subheader(f"Selected Node: {node_labels.get(return_value, return_value)}")
            st.markdown("Node details would be displayed here.")

