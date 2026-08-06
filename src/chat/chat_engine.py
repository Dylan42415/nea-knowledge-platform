"""
Grounded Gemini RAG Chatbot Engine for the Obsidian Vault.
"""
import time
import re
from pathlib import Path
from typing import List, Dict, Any

from src.config import GEMINI_API_KEY, ANALYSIS_MODEL, VAULT_ROOT
from src.chat.vault_index import search_vault_context, rank_vault_notes

def _get_genai_client():
    """Lazily initialize the google.genai client."""
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        return None

SYSTEM_PROMPT = """You are the official NEA Knowledge Platform Assistant.
You have full, authoritative access to the Obsidian Vault knowledge base provided in the context below.

CRITICAL GROUNDING & PRECISION RULES:
1. Answer the user's question directly, clearly, and concisely using the provided Top Vault Notes context.
2. Every entity, concept, location, or organization mentioned MUST be formatted as an Obsidian [[Wikilink]] (e.g. [[Benzene]], [[National Environment Agency]], [[Singapore]]).
3. Every data point, table value, threshold, or statistic must be copied accurately with exact units and cited with its source document and page location (e.g., "— soe_report.pdf, p. 14-15").
4. If the provided context does not contain the answer, explicitly state: "I could not find information about that in the current vault notes. You can upload relevant PDF or GeoJSON files in the sidebar to add it to the vault."
5. Be concise, structured, and helpful. Format responses with direct answers first, followed by key metrics tables and source citations.
"""

def generate_vault_response(messages: List[Dict[str, str]], vault_root: Path = None) -> str:
    """
    Generate a grounded response using high-precision Top-K vault context RAG.

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

    # Retrieve top 3-5 high precision notes
    vault_context = search_vault_context(latest_user_query, vault_root, max_notes=5)

    client = _get_genai_client()
    if client is None:
        return _offline_fallback_response(latest_user_query, vault_root)

    prompt = f"""{SYSTEM_PROMPT}

=== TOP VAULT CONTEXT ===
{vault_context}
=========================

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
                return _offline_fallback_response(latest_user_query, vault_root, note="Gemini API quota exhausted.")
            if attempt == max_retries - 1:
                return _offline_fallback_response(latest_user_query, vault_root, note=f"API connection error: {e}")
            time.sleep(1)

    return _offline_fallback_response(latest_user_query, vault_root)

def _offline_fallback_response(query: str, vault_root: Path, note: str = "") -> str:
    """
    High-precision deterministic fallback answer generator when Gemini API is offline or rate-limited.
    Extracts direct answers from top-ranked notes.
    """
    ranked_notes = rank_vault_notes(query, vault_root, top_k=5)
    if not ranked_notes:
        return f"No direct matches found in local vault for '{query}'. Upload additional datasets to populate the knowledge base."

    top_confidence, top_note = ranked_notes[0]

    res = ""
    if note:
        res += f"*(Note: {note} Generating deterministic answer from highest-confidence Vault note below.)*\n\n"

    res += f"### Top Match (Confidence: {top_confidence:.2f})\n"
    res += f"────────────────────────────\n"
    res += f"📄 **[[{top_note['title']}]]**\n\n"

    res += f"**Answer**:\n"
    res += f"According to the **[[{top_note['title']}]]** knowledge note:\n\n"
    
    # Extract body content (strip title heading if present)
    body_text = top_note['body']
    if body_text.startswith(f"# {top_note['title']}"):
        body_text = body_text.split("\n", 2)[-1].strip()

    res += f"{body_text}\n\n"

    if top_note['source_document']:
        res += f"**Source**:\n"
        res += f"`{top_note['source_document']}`"
        if top_note['source_location']:
            res += f", {top_note['source_location']}"
        res += "\n\n"

    # Extract related concepts
    if len(ranked_notes) > 1:
        res += f"---\n### Related Concepts\n"
        for conf, rnote in ranked_notes[1:]:
            res += f"- [[{rnote['title']}]] ({rnote['type']})\n"

    return res
