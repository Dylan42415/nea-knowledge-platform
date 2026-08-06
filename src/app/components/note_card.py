import streamlit as st
import html

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
    
    tags_html = "".join([f'<span class="note-tag">#{html.escape(tag)}</span>' for tag in tags])
    escaped_title = html.escape(title)
    escaped_note_type = html.escape(note_type.capitalize())
    escaped_preview = html.escape(preview)
    escaped_date = html.escape(date)
    
    card_html = f"""
    <div class="note-card">
        <div class="note-header">
            <h3 class="note-title">{escaped_title}</h3>
            <span class="note-badge" style="background-color: {color}20; color: {color}; border-color: {color}50;">
                {escaped_note_type}
            </span>
        </div>
        <p class="note-preview">{escaped_preview}</p>
        <div class="note-footer">
            <div class="note-tags">{tags_html}</div>
            <span class="note-date">{escaped_date}</span>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
