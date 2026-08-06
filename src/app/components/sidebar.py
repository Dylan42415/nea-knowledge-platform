import streamlit as st

def render_sidebar() -> str:
    """
    Renders the sidebar with navigation, stats, and an ingestion section.
    
    Returns:
        str: The selected navigation option.
    """
    with st.sidebar:
        st.title("🌏 NEA Platform")
        
        st.markdown("---")
        st.subheader("Navigation")
        # Navigation radio
        selected_page = st.radio(
            "Go to",
            ['Dashboard', 'Browse Notes', 'Map View', 'Knowledge Graph'],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.subheader("Platform Stats")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Documents", value="128")
            st.metric(label="Concepts", value="45")
        with col2:
            st.metric(label="Locations", value="67")
            st.metric(label="Active", value="12")
            
        st.markdown("---")
        st.subheader("Ingest New Data")
        uploaded_file = st.file_uploader("Upload Document (PDF, TXT, CSV)", type=["pdf", "txt", "csv"])
        if uploaded_file is not None:
            st.success(f"File {uploaded_file.name} uploaded successfully!")
            
    return selected_page
