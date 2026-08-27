"""
Unit tests for Subject Workspace Manager and Scoped Note Filtering.
"""
import pytest
from pathlib import Path

from src.workspace.workspace_manager import (
    get_workspace_data,
    save_workspace_data,
    create_subject,
    delete_subject,
    assign_files_to_subject,
    get_scoped_notes
)

def test_workspace_crud(tmp_path):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True)

    # 1. Default load
    data = get_workspace_data(vault_dir)
    assert isinstance(data, dict)
    assert "subjects" in data

    # 2. Create subject
    res = create_subject(vault_dir, "Math - Calculus")
    assert res is True
    data_after = get_workspace_data(vault_dir)
    assert "Math - Calculus" in data_after["subjects"]

    # 3. Assign files
    assign_files_to_subject(vault_dir, "Math - Calculus", ["lecture_01.mp3", "lecture_02.mp3"])
    data_files = get_workspace_data(vault_dir)
    assert data_files["subjects"]["Math - Calculus"] == ["lecture_01.mp3", "lecture_02.mp3"]

    # 4. Delete subject
    del_res = delete_subject(vault_dir, "Math - Calculus")
    assert del_res is True
    data_deleted = get_workspace_data(vault_dir)
    assert "Math - Calculus" not in data_deleted["subjects"]

def test_get_scoped_notes(tmp_path):
    vault_dir = tmp_path / "vault"
    concepts_dir = vault_dir / "concepts"
    concepts_dir.mkdir(parents=True)

    # Create dummy notes
    (concepts_dir / "Matrix Inversion.md").write_text("""---
title: Matrix Inversion
type: Concept
source_document: math_lecture.mp3
---

# Matrix Inversion
""", encoding="utf-8")

    (concepts_dir / "Tang Poetry.md").write_text("""---
title: Tang Poetry
type: Concept
source_document: chinese_lecture.mp3
---

# Tang Poetry
""", encoding="utf-8")

    # Test Global Scope
    all_scoped = get_scoped_notes(vault_dir, "All Files (Global Vault)")
    assert len(all_scoped) == 2

    # Test File Scope
    math_file_scoped = get_scoped_notes(vault_dir, "File: math_lecture.mp3")
    assert len(math_file_scoped) == 1
    assert math_file_scoped[0]["title"] == "Matrix Inversion"

    # Test Subject Scope
    create_subject(vault_dir, "Math")
    assign_files_to_subject(vault_dir, "Math", ["math_lecture.mp3"])
    subj_scoped = get_scoped_notes(vault_dir, "Subject: Math")
    assert len(subj_scoped) == 1
    assert subj_scoped[0]["title"] == "Matrix Inversion"
