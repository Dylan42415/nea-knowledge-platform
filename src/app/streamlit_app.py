import streamlit as st

# Set page config FIRST, before any other Streamlit commands
st.set_page_config(
    page_title="NEA Knowledge Platform",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded"
)

import sys
from pathlib import Path

# Ensure project root is in sys.path
_current = Path(__file__).resolve()
for _p in [_current] + list(_current.parents):
    if (_p / "src").is_dir():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

from src.app.components.sidebar import render_sidebar
from src.app.views.browse import render_browse_page
from src.app.views.map_view import render_map_page
from src.app.views.graph_view import render_graph_page
from src.app.views.chat_view import render_chat_page

def apply_custom_css():
    """Applies custom CSS for a high-contrast, crystal-clear dark theme and glassmorphism styling."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {
            font-family: 'Inter', sans-serif;
        }
        
        /* Main background & base typography */
        .stApp {
            background-color: #0b0f17 !important;
            color: #f8fafc !important;
        }

        /* Force Sidebar Theme & High Contrast Readability */
        [data-testid="stSidebar"] {
            background-color: #0f172a !important;
            border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
        }

        [data-testid="stSidebar"] * {
            color: #f8fafc !important;
        }

        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3, 
        [data-testid="stSidebar"] h4 {
            color: #ffffff !important;
            font-weight: 700 !important;
        }

        /* Radio Buttons Navigation Contrast */
        [data-testid="stSidebar"] div[role="radiogroup"] label {
            color: #f8fafc !important;
            font-weight: 500 !important;
            font-size: 1.05rem !important;
            padding: 0.4rem 0.6rem !important;
            border-radius: 6px !important;
            transition: all 0.2s ease !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
            background-color: rgba(56, 189, 248, 0.15) !important;
            color: #38bdf8 !important;
        }

        [data-testid="stSidebar"] [data-testid="stMetricLabel"] {
            color: #94a3b8 !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
        }

        [data-testid="stSidebar"] [data-testid="stMetricValue"] {
            color: #38bdf8 !important;
            -webkit-text-fill-color: #38bdf8 !important;
            font-size: 1.8rem !important;
            font-weight: 700 !important;
        }

        p, span, label, li, td, th {
            color: #e2e8f0 !important;
            font-size: 1rem;
            line-height: 1.6;
        }

        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #ffffff !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }
        
        h1 { font-size: 2.2rem !important; }
        h2 { font-size: 1.75rem !important; color: #38bdf8 !important; }
        h3 { font-size: 1.4rem !important; color: #38bdf8 !important; }

        /* Links and Wikilinks */
        a, .stMarkdown a {
            color: #38bdf8 !important;
            font-weight: 600;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }

        /* Streamlit Chat Messages High Contrast Styling */
        [data-testid="stChatMessage"] {
            background-color: rgba(30, 41, 59, 0.75) !important;
            border: 1px solid rgba(56, 189, 248, 0.25) !important;
            border-radius: 12px !important;
            padding: 1.25rem !important;
            margin-bottom: 1rem !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
        }

        [data-testid="stChatMessage"] p, 
        [data-testid="stChatMessage"] div, 
        [data-testid="stChatMessage"] span,
        [data-testid="stChatMessage"] li {
            color: #f8fafc !important;
            font-size: 1.05rem !important;
        }

        /* Chat Input Box — Black Typed Text on Crisp Background */
        [data-testid="stChatInput"] textarea,
        .stChatInput textarea {
            color: #000000 !important;
            background-color: #ffffff !important;
            font-weight: 500 !important;
            font-size: 1.05rem !important;
        }

        [data-testid="stChatInput"] textarea::placeholder,
        .stChatInput textarea::placeholder {
            color: #64748b !important;
        }

        /* Tables High Contrast Styling */
        table {
            width: 100% !important;
            border-collapse: collapse !important;
            margin: 1rem 0 !important;
            background-color: #1e293b !important;
            border-radius: 8px !important;
            overflow: hidden !important;
            border: 1px solid #334155 !important;
        }

        th {
            background-color: #0f172a !important;
            color: #38bdf8 !important;
            font-weight: 700 !important;
            text-align: left !important;
            padding: 0.75rem 1rem !important;
            border-bottom: 2px solid #334155 !important;
        }

        td {
            padding: 0.75rem 1rem !important;
            border-bottom: 1px solid #334155 !important;
            color: #f1f5f9 !important;
        }

        tr:hover td {
            background-color: rgba(56, 189, 248, 0.08) !important;
        }

        /* Metrics styling */
        [data-testid="stMetricValue"] {
            background: linear-gradient(90deg, #2dd4bf, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
            font-size: 2.2rem;
        }
        
        /* Glassmorphism Note Cards */
        .note-card {
            background: rgba(30, 41, 59, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }
        
        .note-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
            border-color: rgba(56, 189, 248, 0.4);
            background: rgba(30, 41, 59, 0.85);
        }
        
        .note-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }
        
        .note-title {
            margin: 0;
            font-size: 1.25rem;
            font-weight: 600;
            color: #ffffff;
        }
        
        .note-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            border: 1px solid;
        }
        
        .note-preview {
            color: #cbd5e1 !important;
            font-size: 0.95rem;
            line-height: 1.5;
            margin-bottom: 1rem;
        }
        
        /* Blockquote Styling */
        blockquote {
            background-color: rgba(15, 23, 42, 0.6) !important;
            border-left: 4px solid #38bdf8 !important;
            padding: 0.75rem 1.25rem !important;
            margin: 1rem 0 !important;
            border-radius: 0 8px 8px 0 !important;
            color: #f1f5f9 !important;
            font-style: italic;
        }

        /* Buttons */
        .stButton>button {
            background: linear-gradient(90deg, #0ea5e9, #3b82f6) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.6rem 1.2rem !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }
        
        .stButton>button:hover {
            opacity: 0.95 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 15px rgba(14, 165, 233, 0.4) !important;
        }
        </style>
    """, unsafe_allow_html=True)

def render_dashboard():
    """Renders the main dashboard page."""
    from pathlib import Path
    from src.config import VAULT_ROOT

    st.title("Welcome to the NEA Knowledge Platform 🌏")
    st.markdown("""
        <div style="font-size: 1.1rem; color: #94a3b8; margin-bottom: 2rem;">
            A centralized hub for environmental datasets, policies, and concepts. 
            Navigate using the sidebar to explore the knowledge base.
        </div>
    """, unsafe_allow_html=True)
    
    vault_dir = Path(VAULT_ROOT)
    doc_count = len(list((vault_dir / "datasets").rglob("*.md"))) if (vault_dir / "datasets").exists() else 0
    concept_count = len(list((vault_dir / "concepts").rglob("*.md"))) if (vault_dir / "concepts").exists() else 0
    location_count = len(list((vault_dir / "locations").rglob("*.md"))) if (vault_dir / "locations").exists() else 0
    org_count = len(list((vault_dir / "organizations").rglob("*.md"))) if (vault_dir / "organizations").exists() else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Datasets", value=str(doc_count))
    with col2:
        st.metric(label="Total Concepts", value=str(concept_count))
    with col3:
        st.metric(label="Total Locations", value=str(location_count))
    with col4:
        st.metric(label="Organizations", value=str(org_count))
        
    st.markdown("---")
    st.subheader("Recent Activity ⚡")
    
    # Real dynamic recent activity from vault notes
    activities = get_recent_activity(vault_dir, limit=5)
    
    if activities:
        for icon, desc, time_str in activities:
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.03); border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center; border: 1px solid rgba(255,255,255,0.05);">
                <div>
                    <span style="font-size: 1.2rem; margin-right: 1rem;">{icon}</span>
                    <span style="font-weight: 500;">{desc}</span>
                </div>
                <span style="color: #64748b; font-size: 0.85rem;">{time_str}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No recent vault activity found. Upload data to begin.")

def get_recent_activity(vault_dir: Path, limit: int = 5):
    """Scan vault files to dynamically build recent activity feed."""
    import yaml
    import html
    from datetime import datetime

    if not vault_dir.exists():
        return []

    activities = []
    icon_map = {
        "dataset": "📄 Dataset Ingested",
        "concept": "🧠 Concept Extracted",
        "location": "🗺️ Location Mapped",
        "organization": "🏛️ Organization Added"
    }

    for filepath in vault_dir.rglob("*.md"):
        if filepath.name.startswith("_") or filepath.parent.name == "_templates":
            continue
        try:
            mtime = filepath.stat().st_mtime
            content = filepath.read_text(encoding="utf-8")
            title = filepath.stem.replace("_", " ").title()
            ntype = filepath.parent.name.rstrip("s").lower()
            
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    meta = yaml.safe_load(parts[1]) or {}
                    title = meta.get("title", title)
                    ntype = meta.get("type", ntype).lower()
                    
            icon = icon_map.get(ntype, "📝 Note Created")
            activities.append((mtime, icon, title, ntype))
        except Exception:
            continue

    activities.sort(key=lambda x: x[0], reverse=True)
    
    result = []
    now = datetime.now().timestamp()
    for mtime, icon, title, ntype in activities[:limit]:
        diff_sec = max(0, int(now - mtime))
        if diff_sec < 60:
            time_str = "Just now"
        elif diff_sec < 3600:
            time_str = f"{diff_sec // 60}m ago"
        elif diff_sec < 86400:
            time_str = f"{diff_sec // 3600}h ago"
        else:
            time_str = f"{diff_sec // 86400}d ago"
        result.append((icon, html.escape(str(title)), time_str))

    return result

def main():
    apply_custom_css()
    selected_page = render_sidebar()
    
    if selected_page == 'Dashboard':
        render_dashboard()
    elif selected_page == 'Browse Notes':
        render_browse_page()
    elif selected_page == 'Map View':
        render_map_page()
    elif selected_page == 'Knowledge Graph':
        render_graph_page()
    elif selected_page == 'Chat with Vault':
        render_chat_page()

if __name__ == "__main__":
    main()
