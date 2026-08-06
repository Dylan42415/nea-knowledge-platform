import streamlit as st

# Set page config FIRST, before any other Streamlit commands
st.set_page_config(
    page_title="NEA Knowledge Platform",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded"
)

from src.app.components.sidebar import render_sidebar
from src.app.pages.browse import render_browse_page
from src.app.pages.map_view import render_map_page
from src.app.pages.graph_view import render_graph_page

def apply_custom_css():
    """Applies custom CSS for a premium dark theme and glassmorphism styling."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {
            font-family: 'Inter', sans-serif;
        }
        
        /* Main background */
        .stApp {
            background-color: #0e1117;
            color: #f8fafc;
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #f8fafc !important;
            font-weight: 600;
        }
        
        /* Metrics styling */
        [data-testid="stMetricValue"] {
            background: linear-gradient(90deg, #2dd4bf, #0ea5e9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
            font-size: 2rem;
        }
        
        /* Glassmorphism Note Cards */
        .note-card {
            background: rgba(30, 41, 59, 0.4);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        
        .note-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2), 0 4px 6px -2px rgba(0, 0, 0, 0.1);
            border-color: rgba(14, 165, 233, 0.3);
            background: rgba(30, 41, 59, 0.6);
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
        }
        
        .note-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
            border: 1px solid;
        }
        
        .note-preview {
            color: #94a3b8;
            font-size: 0.95rem;
            line-height: 1.5;
            margin-bottom: 1rem;
        }
        
        .note-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(255,255,255,0.05);
            padding-top: 0.75rem;
        }
        
        .note-tags {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        
        .note-tag {
            font-size: 0.75rem;
            color: #64748b;
            background: rgba(255, 255, 255, 0.05);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
        }
        
        .note-date {
            font-size: 0.75rem;
            color: #64748b;
        }
        
        /* Expander tweaks */
        .streamlit-expanderHeader {
            background-color: rgba(30, 41, 59, 0.2);
            border-radius: 8px;
        }
        
        /* Buttons */
        .stButton>button {
            background: linear-gradient(90deg, #0ea5e9, #3b82f6);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 0.5rem 1rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .stButton>button:hover {
            opacity: 0.9;
            transform: scale(1.02);
            box-shadow: 0 0 15px rgba(14, 165, 233, 0.4);
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
    
    # Mock recent activity
    activities = [
        ("🆕 Document Ingested", "Air Quality Report Q2 2026", "2 hours ago"),
        ("🔗 New Relationship Discovered", "Sensor_A23 connects to Dataset_PM2.5", "5 hours ago"),
        ("🗺️ Map Layer Updated", "Waste Collection Zones", "1 day ago"),
        ("🧠 Concept Extracted", "Circular Economy Framework", "2 days ago")
    ]
    
    for icon, desc, time in activities:
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.03); border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center; border: 1px solid rgba(255,255,255,0.05);">
            <div>
                <span style="font-size: 1.2rem; margin-right: 1rem;">{icon}</span>
                <span style="font-weight: 500;">{desc}</span>
            </div>
            <span style="color: #64748b; font-size: 0.85rem;">{time}</span>
        </div>
        """, unsafe_allow_html=True)

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

if __name__ == "__main__":
    main()
