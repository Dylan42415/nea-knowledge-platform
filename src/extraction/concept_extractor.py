import json
import re
import time
import google.generativeai as genai
from typing import Optional
from src.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

def extract_concepts_fallback(text: str) -> list[dict]:
    """
    Fallback method using regex and simple rules.
    """
    entities = []
    
    # Capitalized words for basic concepts/orgs
    matches = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    
    for match in set(matches):
        if len(match) > 3:
            entities.append({
                "name": match,
                "type": "concept",
                "description": "Extracted via fallback mechanism"
            })
            
    return entities

def extract_concepts(text: str, source_context: str = '') -> list[dict]:
    """
    Use Google Generative AI (Gemini) to extract concepts, locations, organizations from text.
    Each extracted entity: {"name": str, "type": "concept"|"location"|"organization", "description": str}
    """
    prompt = f"""
    Extract key concepts, topics, geographic locations, and organizations/agencies from the following text.
    Return the output as a valid JSON array of objects.
    Each object must have exactly these fields:
    - "name": String (the name of the entity)
    - "type": String (must be exactly one of: "concept", "location", "organization")
    - "description": String (a brief description of what this entity is in the context)
    
    Context: {source_context}
    Text: {text}
    
    Output ONLY valid JSON.
    """
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            
            # Clean response text if it contains markdown code blocks
            res_text = response.text.strip()
            if res_text.startswith("```json"):
                res_text = res_text[7:]
            if res_text.endswith("```"):
                res_text = res_text[:-3]
                
            entities = json.loads(res_text.strip())
            return entities
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error calling Gemini after {max_retries} attempts: {e}")
                return extract_concepts_fallback(text)
            time.sleep(2)
            
    return extract_concepts_fallback(text)
