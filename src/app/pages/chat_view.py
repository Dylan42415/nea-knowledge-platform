"""
Streamlit Chat View page for full Obsidian Vault context AI assistant.
"""
import sys
import streamlit as st
from pathlib import Path

# Ensure project root is in sys.path
_current = Path(__file__).resolve()
for _p in [_current] + list(_current.parents):
    if (_p / "src").is_dir():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

from src.chat.chat_engine import generate_vault_response

def render_chat_page():
    """Renders the AI Vault Assistant chatbot page."""
    st.title("💬 Chat with Vault")
    st.markdown("""
        <div style="font-size: 1.05rem; color: #94a3b8; margin-bottom: 1.5rem;">
            Ask any question about your environmental datasets, concepts, locations, and reports. 
            The AI assistant has full context over all <b>Obsidian Vault</b> notes.
        </div>
    """, unsafe_allow_html=True)

    # Initialize chat history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I am your **NEA Knowledge Vault Assistant**. I have full context over all your ingested vault notes. Ask me anything about air quality, pollutants, locations, or environmental standards!"
            }
        ]

    # Suggested Prompts section
    st.markdown("##### 💡 Suggested Questions")
    col1, col2, col3 = st.columns(3)
    selected_prompt = None

    with col1:
        if st.button("📊 Benzene Levels in 2020", use_container_width=True):
            selected_prompt = "What was the average ambient Benzene concentration in 2020 and its historical 5-year range?"
    with col2:
        if st.button("🌫️ PSI Pollutants & Bands", use_container_width=True):
            selected_prompt = "What pollutants are used in the 24-hour PSI computation and what are the health advisory bands?"
    with col3:
        if st.button("🏛️ WHO AQG Standards", use_container_width=True):
            selected_prompt = "Which air quality standards and indicators are benchmarked against the WHO AQG 2005 guidelines?"

    st.markdown("---")

    # Render previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Read user input from input field or suggested prompt button
    user_input = st.chat_input("Ask a question about the NEA Knowledge Vault...")
    prompt = selected_prompt or user_input

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching vault notes & generating grounded answer..."):
                response = generate_vault_response(st.session_state.messages)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()

if __name__ == "__main__" or not __name__.startswith("src."):
    render_chat_page()
