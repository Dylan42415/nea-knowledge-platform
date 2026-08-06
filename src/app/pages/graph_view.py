import os
import re
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import yaml
from src.config import VAULT_ROOT

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
    
    vault_dir = os.path.join(VAULT_ROOT, 'vault')
    if not os.path.exists(vault_dir) or not any(f.endswith('.md') for f in os.listdir(vault_dir)):
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
        
    # Build graph
    nodes = []
    edges = []
    node_ids = set()
    
    type_colors = {
        "dataset": "#3b82f6",     # Blue
        "concept": "#22c55e",     # Green
        "location": "#f97316",    # Orange
        "organization": "#a855f7",# Purple
        "unknown": "#64748b"      # Gray
    }
    
    wikilink_pattern = re.compile(r'\[\[(.*?)\]\]')
    
    for filename in os.listdir(vault_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(vault_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            metadata = parse_frontmatter(content)
            title = metadata.get("title", filename.replace(".md", ""))
            ntype = metadata.get("type", "concept").lower()
            
            if node_type != "All" and ntype != node_type.lower():
                continue
                
            if search_node and search_node.lower() not in title.lower():
                continue
                
            node_id = filename.replace(".md", "")
            node_ids.add(node_id)
            
            nodes.append(Node(
                id=node_id,
                label=title,
                size=25,
                color=type_colors.get(ntype, type_colors["unknown"]),
                title=f"{ntype.capitalize()}: {title}"
            ))
            
            # Find links
            links = wikilink_pattern.findall(content)
            for link in links:
                # Handle aliases [[link|alias]]
                target = link.split('|')[0].strip()
                edges.append(Edge(
                    source=node_id,
                    target=target,
                    color="#475569"
                ))
                
    # Create missing nodes that are linked to but don't exist
    for edge in edges:
        if edge.target not in node_ids:
            nodes.append(Node(
                id=edge.target,
                label=edge.target,
                size=15,
                color=type_colors["unknown"],
                title="Unknown Node"
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
            st.subheader(f"Selected Node: {return_value}")
            st.markdown("Node details would be displayed here.")
