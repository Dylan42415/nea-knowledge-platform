"""
Grounded Gemini RAG Chatbot Engine for the Obsidian Vault.
"""
import time
import re
from pathlib import Path
from typing import List, Dict, Any

from src.config import GEMINI_API_KEY, ANALYSIS_MODEL, VAULT_ROOT
from src.chat.vault_index import search_vault_context, build_vault_index

def _get_genai_client():
    """Lazily initialize the google.genai client."""
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        return None

SYSTEM_PROMPT = """You are the official NEA Knowledge Platform Assistant.
You have full, authoritative access to the Obsidian Vault knowledge base provided in the context below.

CRITICAL GROUNDING RULES:
1. Answer the user's question strictly using the provided Vault Notes context.
2. Every entity, concept, location, or organization mentioned MUST be formatted as an Obsidian [[Wikilink]] (e.g. [[Benzene]], [[National Environment Agency]], [[Singapore]]).
3. Every data point, table value, threshold, or statistic must be copied accurately with exact units and cited with its source document and location (e.g., "— soe_report.pdf, p. 14-15").
4. If the provided context does not contain the answer, explicitly state: "I could not find information about that in the current vault notes. You can upload relevant PDF or GeoJSON files in the sidebar to add it to the vault."
5. Be concise, professional, structured, and helpful. Use markdown bullet points and tables where appropriate.
"""

def generate_vault_response(messages: List[Dict[str, str]], vault_root: Path = None) -> str:
    """
    Generate a grounded response using full vault context RAG.

    Args:
        messages: List of chat message dicts [{'role': 'user'/'assistant', 'content': '...'}]
        vault_root: Optional custom vault root path.

    Returns:
        Grounded answer string formatted with [[Wikilinks]] and citations.
    """
    if vault_root is None:
        vault_root = Path(VAULT_ROOT)

    latest_user_query = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            latest_user_query = msg.get("content", "")
            break

    if not latest_user_query:
        return "Please ask a question about your vault knowledge base."

    # Retrieve relevant vault context
    vault_context = search_vault_context(latest_user_query, vault_root, max_notes=15)

    client = _get_genai_client()
    if client is None:
        return _offline_fallback_response(latest_user_query, vault_root)

    prompt = f"""{SYSTEM_PROMPT}

=== VAULT CONTEXT ===
{vault_context}
=====================

=== CONVERSATION HISTORY ===
"""
    for msg in messages[-5:]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        prompt += f"\n{role}: {msg.get('content')}"

    prompt += f"\n\nAssistant:"

    model = ANALYSIS_MODEL or "gemini-3.1-flash-lite"
    max_retries = 2

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                return _offline_fallback_response(latest_user_query, vault_root, note="Gemini API rate limit reached.")
            if attempt == max_retries - 1:
                return _offline_fallback_response(latest_user_query, vault_root, note=f"API connection error: {e}")
            time.sleep(1)

    return _offline_fallback_response(latest_user_query, vault_root)

def _offline_fallback_response(query: str, vault_root: Path, note: str = "") -> str:
    """Local fallback answer generator when Gemini API is offline or rate-limited."""
    notes = build_vault_index(vault_root)
    
    stop_words = {"what", "was", "the", "and", "for", "with", "how", "does", "which", "where", "from", "its", "are", "have", "been", "that", "this"}
    query_terms = [term for term in re.findall(r'\w+', query.lower()) if len(term) > 2 and term not in stop_words]

    scored_notes = []
    for n in notes:
        title_lower = n['title'].lower()
        body_lower = n['body'].lower()
        score = 0
        for term in query_terms:
            if term in title_lower:
                score += 10
            score += len(re.findall(r'\b' + re.escape(term) + r'\b', body_lower))
        if score > 0:
            scored_notes.append((score, n))

    scored_notes.sort(key=lambda x: x[0], reverse=True)
    matching_notes = [n for s, n in scored_notes[:5]]

    res = ""
    if note:
        res += f"*(Note: {note} Generating answer from local Vault notes below.)*\n\n"

    if matching_notes:
        top_note = matching_notes[0]
        res += f"### Answer from Vault: [[{top_note['title']}]]\n"
        if top_note['source_document']:
            res += f"**Source**: {top_note['source_document']}"
            if top_note['source_location']:
                res += f", {top_note['source_location']}"
            res += "\n\n"
        res += f"{top_note['body']}\n"
        
        if len(matching_notes) > 1:
            res += "\n---\n**Related Vault Notes**:\n"
            for n in matching_notes[1:]:
                res += f"- [[{n['title']}]] ({n['type']})\n"
    else:
        res += f"No direct matches found in local vault for '{query}'. Upload additional datasets to populate the knowledge base."

    return res
