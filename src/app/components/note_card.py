import streamlit as st

def render_note_card(title: str, note_type: str, tags: list[str], preview: str, date: str) -> None:
    """
    Renders a styled card for a vault note using custom HTML/CSS.
    
    Args:
        title (str): Note title.
        note_type (str): Type of note (dataset, concept, location, organization).
        tags (list[str]): List of tags.
        preview (str): Preview snippet.
        date (str): Ingestion date.
    """
    type_colors = {
        "dataset": "#3b82f6",     # Blue
        "concept": "#22c55e",     # Green
        "location": "#f97316",    # Orange
        "organization": "#a855f7" # Purple
    }
    
    color = type_colors.get(note_type.lower(), "#64748b") # Default gray
    
    tags_html = "".join([f'<span class="note-tag">#{tag}</span>' for tag in tags])
    
    card_html = f"""
    <div class="note-card">
        <div class="note-header">
            <h3 class="note-title">{title}</h3>
            <span class="note-badge" style="background-color: {color}20; color: {color}; border-color: {color}50;">
                {note_type.capitalize()}
            </span>
        </div>
        <p class="note-preview">{preview}</p>
        <div class="note-footer">
            <div class="note-tags">{tags_html}</div>
            <span class="note-date">{date}</span>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
