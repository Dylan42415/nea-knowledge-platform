import json
import re
import time
from typing import Optional

from src.config import GEMINI_API_KEY, ANALYSIS_MODEL


def _get_genai_client():
    """Lazily initialize the google.genai client."""
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        return client
    except ImportError:
        return None


def extract_concepts_fallback(text: str) -> list[dict]:
    """Fallback method using regex and simple heuristics when Gemini is unavailable."""
    entities: list[dict] = []

    # Capitalized multi-word phrases as candidate concepts/orgs
    matches = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
    for match in set(matches):
        if len(match) > 3:
            entities.append({
                "name": match,
                "type": "concept",
                "description": "Extracted via fallback mechanism",
            })

    return entities


def extract_concepts(text: str, source_context: str = '') -> list[dict]:
    """Use Google Gemini to extract concepts, locations, and organizations.

    Args:
        text: The text to extract entities from.
        source_context: Optional context about the source document.

    Returns:
        List of dicts, each with keys: name, type, description.
    """
    client = _get_genai_client()
    if client is None:
        return extract_concepts_fallback(text)

    prompt = (
        "Extract key concepts, topics, geographic locations, and "
        "organizations/agencies from the following text.\n"
        "Return the output as a valid JSON array of objects.\n"
        "Each object must have exactly these fields:\n"
        '- "name": String (the name of the entity)\n'
        '- "type": String (must be exactly one of: "concept", "location", "organization")\n'
        '- "description": String (a brief description in context)\n\n'
        f"Context: {source_context}\nText: {text}\n\nOutput ONLY valid JSON."
    )

    model = ANALYSIS_MODEL or "gemini-2.0-flash-lite"
    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            res_text = response.text.strip()
            if res_text.startswith("```json"):
                res_text = res_text[7:]
            if res_text.endswith("```"):
                res_text = res_text[:-3]
            return json.loads(res_text.strip())
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error calling Gemini after {max_retries} attempts: {e}")
                return extract_concepts_fallback(text)
            time.sleep(2)

    return extract_concepts_fallback(text)

