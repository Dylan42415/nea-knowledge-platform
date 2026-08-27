"""
Hidden Insights & Audio Summary Extractor Engine.
"""
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from src.config import GEMINI_API_KEY, ANALYSIS_MODEL
from src.chat.vault_index import build_vault_index

logger = logging.getLogger(__name__)

def _get_genai_client():
    """Lazily initialize the google.genai client."""
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        return None

INSIGHT_PROMPT = """You are an elite academic study strategist and exam insight extractor.
Your job is to analyze lecture notes and extract hidden insights, executive audio summaries, formula cheat sheets, and exam traps.

CRITICAL INSTRUCTIONS:
1. Provide an Executive Lecture Summary (3-4 bullet points).
2. Extract "Hidden Insights" (implicit connections between concepts that professor implied).
3. Extract "Exam Alerts & Common Pitfalls" (things students often get wrong on tests).
4. Build a "Formula & Definitions Cheat Sheet" table.
5. Output ONLY valid JSON in this schema:
{
  "executive_summary": [
    "Summary point 1...",
    "Summary point 2..."
  ],
  "hidden_insights": [
    {
      "title": "Insight 1 Title",
      "description": "Deep connection explanation...",
      "related_concepts": ["ConceptA", "ConceptB"]
    }
  ],
  "exam_alerts": [
    {
      "warning": "Confusing Precision and Recall",
      "explanation": "Precision measures false positives; recall measures false negatives. Questions often swap these."
    }
  ],
  "cheat_sheet": [
    {"term": "Formula / Term", "definition": "Exact definition or equation", "usage": "When to apply"}
  ]
}
"""

def extract_study_insights(vault_root: Path) -> Dict[str, Any]:
    """
    Extract hidden study insights and audio summary from vault context.
    
    Args:
        vault_root: Path to Obsidian Vault root.
        
    Returns:
        Dict containing executive_summary, hidden_insights, exam_alerts, and cheat_sheet.
    """
    notes = build_vault_index(vault_root)
    if not notes:
        return _offline_insights_fallback([])

    client = _get_genai_client()
    if client is None or not GEMINI_API_KEY:
        return _offline_insights_fallback(notes)

    sample_notes = notes[:12]
    context_str = "\n\n".join([f"=== NOTE: [[{n['title']}]] ({n['type']}) ===\n{n['body']}" for n in sample_notes])

    prompt = f"""{INSIGHT_PROMPT}

=== LECTURE VAULT CONTEXT ===
{context_str}
=============================

Extract executive summary, hidden insights, exam alerts, and cheat sheet:"""

    try:
        response = client.models.generate_content(
            model=ANALYSIS_MODEL or "gemini-3.5-flash-lite",
            contents=prompt
        )
        res_text = response.text.strip()
        if res_text.startswith("```json"):
            res_text = res_text[7:]
        if res_text.startswith("```"):
            res_text = res_text[3:]
        if res_text.endswith("```"):
            res_text = res_text[:-3]

        insights_data = json.loads(res_text.strip())
        if isinstance(insights_data, dict):
            return insights_data
    except Exception as e:
        logger.error(f"Error extracting study insights with Gemini: {e}")

    return _offline_insights_fallback(notes)

def _offline_insights_fallback(notes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Offline fallback insight extractor from vault notes.
    """
    if not notes:
        return {
            "executive_summary": [
                "No lecture notes currently ingested in the vault.",
                "Upload or record a lecture audio file to automatically extract concepts and hidden insights."
            ],
            "hidden_insights": [
                {
                    "title": "Knowledge Graph Synergy",
                    "description": "Connecting concepts with [[Wikilinks]] unlocks higher-order reasoning during exam problem solving.",
                    "related_concepts": ["Active Recall", "Concept Graph"]
                }
            ],
            "exam_alerts": [
                {
                    "warning": "Empty Vault Notice",
                    "explanation": "Record a lecture or upload audio to generate real-time exam alerts."
                }
            ],
            "cheat_sheet": [
                {"term": "Sample Term", "definition": "Sample Definition", "usage": "General Study"}
            ]
        }

    titles = [f"[[{n['title']}]]" for n in notes[:5]]
    
    exec_summary = [
        f"The lecture corpus currently covers {len(notes)} core knowledge concepts including {', '.join(titles[:3])}.",
        "Key focus areas center around mathematical update rules, empirical benchmarks, and operational bounds.",
        "Cross-concept wikilinks establish associative relationships between primary algorithms and practical evaluations."
    ]

    hidden_insights = []
    for n in notes[:3]:
        title = n['title']
        body = n['body']
        wikilinks = [w for w in body.split("[[") if "]]" in w]
        linked = [w.split("]]")[0] for w in wikilinks[:3] if w.split("]]")[0] != title]

        hidden_insights.append({
            "title": f"Cross-Domain Link: [[{title}]]",
            "description": f"The note [[{title}]] serves as a critical node connecting related topics ({', '.join(['[[' + l + ']]' for l in linked]) if linked else 'fundamental concepts'}). Mastering this node bridges conceptual understanding across sections.",
            "related_concepts": linked if linked else [title]
        })

    exam_alerts = [
        {
            "warning": "Precision vs. Recall Ambiguity",
            "explanation": "Exam questions often present edge cases where false positives are costly (requires high precision) versus where false negatives are dangerous (requires high recall)."
        },
        {
            "warning": "Overfitting on Validation Set",
            "explanation": "Do not tune hyperparameters directly on the test set; hyperparameter tuning must only occur on the validation split."
        }
    ]

    cheat_sheet = []
    for n in notes[:6]:
        title = n['title']
        body = n['body']
        def_line = "Core academic definition recorded in vault."
        if "## Summary" in body:
            def_line = body.split("## Summary", 1)[-1].split("##", 1)[0].strip().replace("\n", " ")
        
        cheat_sheet.append({
            "term": title,
            "definition": def_line[:120] + "...",
            "usage": f"Key concept in {n.get('source_document', 'Lecture Note')}"
        })

    return {
        "executive_summary": exec_summary,
        "hidden_insights": hidden_insights,
        "exam_alerts": exam_alerts,
        "cheat_sheet": cheat_sheet
    }
