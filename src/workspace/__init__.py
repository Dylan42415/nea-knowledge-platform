"""
Workspace package.
"""
from src.workspace.workspace_manager import (
    get_workspace_data,
    save_workspace_data,
    create_subject,
    delete_subject,
    assign_files_to_subject,
    get_all_lecture_files,
    get_scoped_notes
)

__all__ = [
    "get_workspace_data",
    "save_workspace_data",
    "create_subject",
    "delete_subject",
    "assign_files_to_subject",
    "get_all_lecture_files",
    "get_scoped_notes"
]
