import streamlit as st

# Set page config FIRST, before any other Streamlit commands
st.set_page_config(
    page_title="StudyGraph AI — Lecture & YouTube Knowledge Graph Platform",
    page_icon="🎓",
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
from src.app.views.workspace_view import render_workspace_view
from src.app.views.lecture_recorder import render_lecture_recorder_view
from src.app.views.graph_view import render_graph_page
from src.app.views.study_guide_view import render_study_guide_view
from src.app.views.quiz_view import render_quiz_view
from src.app.views.browse import render_browse_page
from src.workspace.workspace_manager import is_valid_scope_selected

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

def main():
    apply_custom_css()
    selected_page = render_sidebar()
    active_scope = st.session_state.get("active_study_scope", "")
    scope_valid = is_valid_scope_selected(active_scope)

    if selected_page == '📁 Subject Workspaces':
        render_workspace_view()
    elif selected_page == '🎙️ Ingest Lecture / YouTube':
        render_lecture_recorder_view()
    elif selected_page == '🕸️ Knowledge Graph & Chat':
        render_graph_page()
    elif selected_page == '💡 Study Guide & Insights':
        render_study_guide_view()
    elif selected_page == '📝 Active Recall Quiz':
        render_quiz_view()
    elif selected_page == '📖 Browse Study Notes':
        render_browse_page()
    else:
        render_workspace_view()

if __name__ == "__main__":
    main()
