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
    """Use Google Gemini to extract concepts, locations, and organizations
    following Gold Standard knowledge extraction principles.

    Args:
        text: The text to extract entities from.
        source_context: Optional context about the source document and page numbers.

    Returns:
        List of dicts, each with keys: name, type, summary, source_location, key_data, relationships, excerpt.
    """
    client = _get_genai_client()
    if client is None:
        return extract_concepts_fallback(text)

    prompt = (
        "You are an expert knowledge extraction engine for NEA environmental documents.\n"
        "Extract key concepts, geographic locations, and organizations from the source text below.\n"
        "Follow these Gold Standard Extraction Principles:\n"
        "1. Maximize real content, data tables, exact numerical thresholds, and exact units.\n"
        "2. Copy numbers, units, and dates exactly as given (e.g., '20 µg/m³', '24-hour mean').\n"
        "3. Include typed relationships between entities ONLY where explicitly supported by text (e.g. COMPUTED_FROM, BENCHMARKED_AGAINST, MANAGED_BY, LOCATED_IN).\n"
        "4. Include exact source location/page citations and verbatim excerpts where available.\n\n"
        "Return the output as a valid JSON array of objects.\n"
        "Each object must have these exact fields:\n"
        '- "name": String (the clean name of the entity)\n'
        '- "type": String (one of: "concept", "location", "organization")\n'
        '- "summary": String (1-3 sentences concise specific summary)\n'
        '- "source_location": String (e.g., "p. 6, section \'PSI\'")\n'
        '- "key_data": String (Markdown formatted tables, data thresholds, or exact statistics, or "" if none)\n'
        '- "relationships": Array of objects [{"predicate": "COMPUTED_FROM", "target": "PM2.5"}]\n'
        '- "excerpt": String (verbatim source quote or "" if none)\n\n'
        f"Source Context: {source_context}\nText: {text}\n\nOutput ONLY valid JSON."
    )

    model = ANALYSIS_MODEL or "gemini-3.1-flash-lite"
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
            if res_text.startswith("```"):
                res_text = res_text[3:]
            if res_text.endswith("```"):
                res_text = res_text[:-3]
            data = json.loads(res_text.strip())
            if isinstance(data, list):
                return data
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error calling Gemini after {max_retries} attempts: {e}")
                return extract_concepts_fallback(text)
            time.sleep(2)

    return extract_concepts_fallback(text)

