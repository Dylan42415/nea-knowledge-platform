from pathlib import Path
import re

def create_wikilinks(concepts: list[str]) -> str:
    """
    Convert concept names to [[wikilink]] format.
    """
    return " ".join([f"[[{concept}]]" for concept in concepts])

def resolve_backlinks(vault_root: Path, note_path: Path) -> list[str]:
    """
    Scan vault for notes that should link to this note.
    """
    backlinks = []
    note_name = note_path.stem
    
    for file_path in vault_root.rglob("*.md"):
        if file_path == note_path:
            continue
            
        try:
            content = file_path.read_text(encoding='utf-8')
            if f"[[{note_name}]]" in content:
                backlinks.append(file_path.stem)
        except UnicodeDecodeError:
            continue
            
    return backlinks

def update_links_in_note(note_path: Path, new_links: list[str]) -> None:
    """
    Append new wikilinks to an existing note's Related section.
    """
    content = note_path.read_text(encoding='utf-8')
    
    new_links_str = "\n".join([f"- [[{link}]]" for link in new_links])
    
    if "## Related" in content:
        content = content.replace("## Related\n", f"## Related\n{new_links_str}\n")
    else:
        content += f"\n\n## Related\n{new_links_str}\n"
        
    note_path.write_text(content, encoding='utf-8')
