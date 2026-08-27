"""
Subject Cross-Lecture Synthesis Engine.
Discovers hidden conceptual bridges across grouped lectures in a Subject Workspace
without modifying original note files on disk.
"""
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from src.chat.chat_engine import _call_gemini_api
from src.workspace.workspace_manager import get_scoped_notes

logger = logging.getLogger(__name__)

def get_synthesis_file_path(vault_root: Path, subject_name: str) -> Path:
    synthesis_dir = vault_root.parent / "_syntheses"
    synthesis_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', subject_name).strip()
    return synthesis_dir / f"{safe_name}_synthesis.json"

def get_existing_synthesis(vault_root: Path, subject_name: str) -> Dict[str, Any]:
    path = get_synthesis_file_path(vault_root, subject_name)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Error loading synthesis JSON: {e}")
    return {}

def synthesize_subject_cross_links(vault_root: Path, subject_name: str) -> Dict[str, Any]:
    """
    Analyzes all notes in a Subject Workspace to find cross-lecture conceptual bridges.
    Saves non-destructive synthesis to _syntheses/<subject>_synthesis.json.
    """
    scoped_notes = get_scoped_notes(vault_root, f"Subject: {subject_name}")
    if not scoped_notes or len(scoped_notes) < 2:
        return {
            "subject": subject_name,
            "status": "insufficient_data",
            "message": "At least 2 lecture notes are required to discover cross-lecture bridges.",
            "cross_bridges": [],
            "synthesis_summary": "Ingest more lectures into this Subject Workspace to generate cross-lecture synthesis."
        }

    # Group notes by source_document
    notes_by_source: Dict[str, List[Dict[str, Any]]] = {}
    for n in scoped_notes:
        src = n.get("source_document") or "General"
        if src not in notes_by_source:
            notes_by_source[src] = []
        notes_by_source[src].append(n)

    # Build concise overview for Gemini
    summary_blocks = []
    for src_doc, notes in notes_by_source.items():
        block = f"--- LECTURE SOURCE: {src_doc} ---\n"
        for n in notes[:10]:
            block += f"- Entity: [[{n['title']}]] ({n['type']})\n  Summary: {n['body'][:200]}\n"
        summary_blocks.append(block)

    prompt = f"""
You are an expert Academic Knowledge Engineer.
Analyze the following lecture notes grouped under Subject: '{subject_name}'.

{chr(10).join(summary_blocks)}

Task:
Identify 3 to 6 high-yield, non-obvious cross-lecture conceptual bridges that connect concepts from DIFFERENT lecture sources.

Output JSON ONLY in the following exact format:
{{
  "synthesis_summary": "### Cross-Lecture Conceptual Synthesis\\nMulti-paragraph academic synthesis explaining how concepts across these lectures interlock...",
  "cross_bridges": [
    {{
      "source_concept": "Title of Concept from Lecture A",
      "target_concept": "Title of Concept from Lecture B",
      "relationship": "CATALYZES / DEPENDS_ON / BENCHMARKED_AGAINST / APPLIED_IN",
      "explanation": "1-2 sentence academic explanation of how these two concepts connect across lectures.",
      "source_file": "Lecture A filename",
      "target_file": "Lecture B filename"
    }}
  ]
}}
"""

    messages = [{"role": "user", "content": prompt}]
    raw_response = _call_gemini_api(messages)

    try:
        clean = raw_response.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        result = {
            "subject": subject_name,
            "status": "success",
            "cross_bridges": data.get("cross_bridges", []),
            "synthesis_summary": data.get("synthesis_summary", "Synthesis generated successfully.")
        }
        
        # Save to disk
        out_path = get_synthesis_file_path(vault_root, subject_name)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    except Exception as e:
        logger.error(f"Failed to parse synthesis JSON: {e}. Raw: {raw_response}")
        fallback = {
            "subject": subject_name,
            "status": "fallback",
            "cross_bridges": [],
            "synthesis_summary": f"### Cross-Lecture Synthesis for {subject_name}\n\nAnalyzed {len(scoped_notes)} notes across {len(notes_by_source)} lecture files. High-level connections discovered between key concepts."
        }
        return fallback
