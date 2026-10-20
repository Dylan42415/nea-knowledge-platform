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
    """Applies clean custom CSS refinements over native Streamlit Dark Theme."""
    st.markdown("""
        <style>
        /* Remove gray running/stale overlay */
        .stApp > div[data-test-script-state="running"] {
            opacity: 1.0 !important;
        }

        /* High Contrast Headers */
        h1, h2, h3, h4 {
            color: #ffffff !important;
            font-weight: 700 !important;
        }
        
        h2, h3 { color: #38bdf8 !important; }

        /* Streamlit Chat Messages High Contrast */
        [data-testid="stChatMessage"] {
            background-color: #1e293b !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
            padding: 1rem 1.25rem !important;
            margin-bottom: 0.75rem !important;
        }

        /* Chat Input Box — Black Typed Text on Crisp Background */
        [data-testid="stChatInput"] textarea,
        .stChatInput textarea {
            color: #000000 !important;
            background-color: #ffffff !important;
            font-weight: 500 !important;
            font-size: 1.05rem !important;
        }

        /* High Contrast Tables */
        table {
            width: 100% !important;
            border-collapse: collapse !important;
            margin: 1rem 0 !important;
            background-color: #1e293b !important;
            border-radius: 8px !important;
            border: 1px solid #334155 !important;
        }

        th {
            background-color: #0f172a !important;
            color: #38bdf8 !important;
            font-weight: 700 !important;
            padding: 0.75rem 1rem !important;
            border-bottom: 2px solid #334155 !important;
        }

        td {
            padding: 0.75rem 1rem !important;
            border-bottom: 1px solid #334155 !important;
            color: #f1f5f9 !important;
        }

        /* Primary Action Buttons */
        .stButton>button {
            background: linear-gradient(90deg, #0ea5e9, #3b82f6) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.6rem 1.2rem !important;
            font-weight: 600 !important;
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
