"""
Interactive Recall Quiz & Flashcard Generator Engine.
Supports dynamic AI question generation, question randomization, and quiz re-attempts.
"""
import time
import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Any

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

QUIZ_PROMPT = """You are an academic exam generator specializing in active recall, flashcards, and conceptual understanding.
Based on the provided lecture notes and concept vault context, generate an interactive recall test.

CRITICAL INSTRUCTIONS:
1. Create 5-8 high-yield questions covering key definitions, formulas, relationships, and exam alerts.
2. Include a mix of Multiple Choice questions (with 4 options) and Flashcards (front/back).
3. Provide clear explanations for the correct answers referencing the concept note.
4. Output ONLY valid JSON matching this schema:
[
  {
    "id": 1,
    "type": "multiple_choice",
    "concept": "Gradient Descent",
    "question": "What happens if the learning rate alpha is set too high during Gradient Descent?",
    "options": [
      "A. The algorithm converges faster to global minimum",
      "B. The algorithm may overshoot the minimum and diverge",
      "C. The loss function becomes strictly zero",
      "D. Gradient becomes infinite immediately"
    ],
    "answer": "B. The algorithm may overshoot the minimum and diverge",
    "explanation": "A high learning rate causes large weight updates, skipping over local minima and causing loss divergence."
  },
  {
    "id": 2,
    "type": "flashcard",
    "concept": "Backpropagation",
    "question": "What is the core mathematical tool used in Backpropagation to compute derivatives?",
    "answer": "The Chain Rule of Calculus",
    "explanation": "Backpropagation recursively applies the Chain Rule to compute partial derivatives of loss with respect to each weight."
  }
]
"""

def generate_quiz(vault_root: Path, force_new: bool = False, seed: int = None) -> List[Dict[str, Any]]:
    """
    Generate or retrieve quiz questions from the lecture knowledge vault.
    
    Args:
        vault_root: Path to Obsidian Vault root directory.
        force_new: If True, calls LLM for a fresh pool of questions.
        seed: Optional integer seed for randomization.

    Returns:
        List of quiz question dicts.
    """
    notes = build_vault_index(vault_root)
    if not notes:
        return _offline_quiz_fallback([])

    client = _get_genai_client()
    if client is None or not GEMINI_API_KEY or not force_new:
        return _offline_quiz_fallback(notes, seed=seed)

    # Build context sample from top 10 notes
    sample_notes = notes[:10]
    context_str = "\n\n".join([f"=== NOTE: {n['title']} ===\n{n['body']}" for n in sample_notes])

    prompt = f"""{QUIZ_PROMPT}

=== LECTURE VAULT CONTEXT ===
{context_str}
=============================

Generate a fresh interactive recall test:"""

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

        questions = json.loads(res_text.strip())
        if isinstance(questions, list) and len(questions) > 0:
            return questions
    except Exception as e:
        logger.error(f"Error generating quiz with Gemini: {e}")

    return _offline_quiz_fallback(notes, seed=seed)

def _offline_quiz_fallback(notes: List[Dict[str, Any]], seed: int = None) -> List[Dict[str, Any]]:
    """
    Offline fallback quiz generator based on vault notes.
    Generates dynamic active recall questions from note titles, key data, and summaries.
    """
    if seed is not None:
        random.seed(seed)
    else:
        random.seed(int(time.time()) % 1000)

    questions = []
    q_id = 1

    if not notes:
        # Default starter questions if vault is completely empty
        return [
            {
                "id": 1,
                "type": "multiple_choice",
                "concept": "Active Recall Method",
                "question": "Which study technique has been empirically proven to provide highest long-term retention for exam preparation?",
                "options": [
                    "A. Passive re-reading of notes",
                    "B. Active Recall and Spaced Repetition",
                    "C. Highlighting textbook pages",
                    "D. Cramming the night before"
                ],
                "answer": "B. Active Recall and Spaced Repetition",
                "explanation": "Active recall forces the brain to retrieve information, strengthening neural pathways for long-term memory."
            },
            {
                "id": 2,
                "type": "flashcard",
                "concept": "Knowledge Graph Linking",
                "question": "What is the primary benefit of linking concepts with [[Wikilinks]] in study notes?",
                "answer": "Creates non-linear associative connections between related lecture concepts.",
                "explanation": "Associative networks mirror cognitive mental models, helping students synthesize cross-chapter topics."
            }
        ]

    selected_notes = random.sample(notes, min(len(notes), 6))

    for note in selected_notes:
        title = note['title']
        body = note['body']
        aliases = note.get('aliases', [])

        # Multiple choice question based on summary
        summary = ""
        if "## Summary" in body:
            summary = body.split("## Summary", 1)[-1].split("##", 1)[0].strip()

        if summary:
            # Generate options
            correct = f"A. {summary[:120]}..."
            wrong_1 = f"B. {title} is an obsolete standard deprecated in modern frameworks."
            wrong_2 = f"C. {title} refers exclusively to unmonitored hardware metrics."
            wrong_3 = f"D. {title} is an external benchmark with zero internal relationship."

            opts = [correct, wrong_1, wrong_2, wrong_3]
            random.shuffle(opts)

            questions.append({
                "id": q_id,
                "type": "multiple_choice",
                "concept": title,
                "question": f"Which of the following best describes the key definition and role of [[{title}]]?",
                "options": opts,
                "answer": correct,
                "explanation": f"Based on lecture note [[{title}]]: {summary[:200]}"
            })
            q_id += 1

        # Flashcard question based on key data / excerpt
        if "## Key Data / Findings" in body:
            tbl = body.split("## Key Data / Findings", 1)[-1].split("##", 1)[0].strip()
            first_lines = [l for l in tbl.splitlines() if "|" in l and "---" not in l][:3]
            data_snippet = "\n".join(first_lines)

            questions.append({
                "id": q_id,
                "type": "flashcard",
                "concept": title,
                "question": f"What key mathematical bounds, parameters, or standards govern [[{title}]]?",
                "answer": f"Key Findings for [[{title}]]:\n\n{data_snippet}",
                "explanation": f"Full metrics are recorded under ## Key Data / Findings in note [[{title}]]."
            })
            q_id += 1

    return questions if questions else _offline_quiz_fallback([])
