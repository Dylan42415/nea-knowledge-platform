"""
Subject Workspace & File Grouping Manager.
Allows STEM students to group files into subjects (e.g. Math, Physics, Chinese)
and filter Knowledge Graphs, Chatbots, Study Guides, and Quizzes by active scope.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

from src.chat.vault_index import build_vault_index

logger = logging.getLogger(__name__)

def _get_workspace_json_path(vault_root: Path) -> Path:
    return vault_root.parent / "workspaces.json"

def get_workspace_data(vault_root: Path) -> Dict[str, Any]:
    """Retrieve subject metadata and file grouping mapping."""
    json_path = _get_workspace_json_path(vault_root)
    if json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Error loading workspace JSON: {e}")

    return {
        "subjects": {
            "General Studies": []
        },
        "active_scope": "-- Select a Subject or File --"
    }

def save_workspace_data(vault_root: Path, data: Dict[str, Any]) -> None:
    """Save subject workspace groupings to JSON."""
    json_path = _get_workspace_json_path(vault_root)
    try:
        json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Error saving workspace JSON: {e}")

def create_subject(vault_root: Path, subject_name: str) -> bool:
    """Create a new subject group."""
    data = get_workspace_data(vault_root)
    clean_name = subject_name.strip()
    if not clean_name or clean_name in data.get("subjects", {}):
        return False

    data["subjects"][clean_name] = []
    save_workspace_data(vault_root, data)
    return True

def delete_subject(vault_root: Path, subject_name: str) -> bool:
    """Delete a subject group."""
    data = get_workspace_data(vault_root)
    if subject_name in data.get("subjects", {}):
        del data["subjects"][subject_name]
        save_workspace_data(vault_root, data)
        return True
    return False

def assign_files_to_subject(vault_root: Path, subject_name: str, filenames: List[str]) -> None:
    """Assign a list of lecture source filenames to a subject group."""
    data = get_workspace_data(vault_root)
    if subject_name not in data.get("subjects", {}):
        data["subjects"][subject_name] = []

    data["subjects"][subject_name] = sorted(list(set(filenames)))
    save_workspace_data(vault_root, data)

def get_all_lecture_files(vault_root: Path) -> List[str]:
    """Scan vault datasets folder for all ingested lecture source filenames."""
    datasets_dir = vault_root / "datasets"
    if not datasets_dir.exists():
        return []

    files = []
    for f in datasets_dir.rglob("*.md"):
        files.append(f.stem)
    return sorted(files)

def is_valid_scope_selected(active_scope: str) -> bool:
    """Check if a valid subject, file, or global scope has been explicitly selected."""
    if not active_scope or active_scope.startswith("--"):
        return False
    return True

def get_scoped_notes(vault_root: Path, active_scope: str) -> List[Dict[str, Any]]:
    """
    Filter all vault notes based on active study scope.
    """
    all_notes = build_vault_index(vault_root)
    if not all_notes or not is_valid_scope_selected(active_scope) or active_scope.startswith("🌐 All Files"):
        return all_notes

    data = get_workspace_data(vault_root)

    # 1. Subject Scope Filtering
    if active_scope.startswith("Subject: "):
        subj_name = active_scope.replace("Subject: ", "").strip()
        assigned_files = set(data.get("subjects", {}).get(subj_name, []))

        if not assigned_files:
            return all_notes

        scoped_notes = []
        for note in all_notes:
            source = note.get("source_document", "")
            title = note.get("title", "")
            raw = note.get("raw_content", "")

            if any(af in source or af in title or af in raw for af in assigned_files):
                scoped_notes.append(note)

        return scoped_notes if scoped_notes else all_notes

    # 2. File Scope Filtering
    if active_scope.startswith("File: "):
        file_name = active_scope.replace("File: ", "").strip()
        scoped_notes = []
        for note in all_notes:
            source = note.get("source_document", "")
            title = note.get("title", "")
            raw = note.get("raw_content", "")

            if file_name in source or file_name in title or file_name in raw:
                scoped_notes.append(note)

        return scoped_notes if scoped_notes else all_notes

    return all_notes
