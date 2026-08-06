import streamlit as st

def render_search_bar() -> str:
    """
    Renders a styled search bar and returns the query.
    
    Returns:
        str: The search query.
    """
    st.markdown("""
        <style>
        .search-container {
            margin-bottom: 2rem;
            position: relative;
        }
        .stTextInput > div > div > input {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #fff;
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        .stTextInput > div > div > input:focus {
            background: rgba(255, 255, 255, 0.1);
            border-color: #0ea5e9;
            box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.2);
        }
        </style>
    """, unsafe_allow_html=True)
    
    query = st.text_input("🔍 Search Knowledge Base...", placeholder="Search notes, concepts, locations...")
    return query
