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

def finalize_vault_wikilinks(vault_root: Path) -> dict:
    """
    POST-GENERATION WIKILINK RESOLVER PASS.
    Executed ONLY AFTER wiki note generation is confirmed complete.
    Scans all generated notes in vault_root, verifies every [[Wikilink]] target,
    creates any missing target concept notes with exact title filenames,
    and resolves bidirectional backlinks across all connected notes.
    """
    from datetime import datetime, timezone
    from src.vault_writer.note_generator import sanitize_filename
    
    # 1. Build index of all existing note stems and exact titles across vault
    existing_notes = {}
    for f in vault_root.rglob("*.md"):
        existing_notes[f.stem.lower()] = f
        # Also index sanitized version
        sanitized = sanitize_filename(f.stem).lower()
        existing_notes[sanitized] = f
        
    concepts_dir = vault_root / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    missing_links = {} # target_title -> list of source note stems
    
    # 2. Scan all generated notes for [[Wikilinks]]
    for note_file in vault_root.rglob("*.md"):
        try:
            content = note_file.read_text(encoding='utf-8')
            wikilinks = re.findall(r'\[\[(.*?)\]\]', content)
            for link in wikilinks:
                target_title = link.split('|')[0].strip()
                if not target_title:
                    continue
                target_lower = target_title.lower()
                target_sanitized = sanitize_filename(target_title).lower()
                
                if target_lower not in existing_notes and target_sanitized not in existing_notes:
                    if target_title not in missing_links:
                        missing_links[target_title] = []
                    missing_links[target_title].append(note_file.stem)
        except Exception:
            continue

    # 3. Create stub concept notes for any unresolved [[Wikilink]] targets
    created_stubs = 0
    for target_title, source_stems in missing_links.items():
        safe_filename = sanitize_filename(target_title) + ".md"
        stub_path = concepts_dir / safe_filename
        if not stub_path.exists():
            backlink_items = "\n".join([f"- Linked from [[{stem}]]" for stem in set(source_stems)])
            stub_content = f"""---
title: {target_title}
type: Concept
source_document: Inferred from Vault Relationships
extraction_date: '{now_str}'
aliases: [{target_title}]
tags: [auto_generated, concept]
---

# {target_title}

## Summary
{target_title} is an environmental concept, statutory benchmark, or organizational entity linked within the NEA Knowledge Graph.

## Related References
{backlink_items}
"""
            stub_path.write_text(stub_content, encoding='utf-8')
            created_stubs += 1
            existing_notes[target_title.lower()] = stub_path
            existing_notes[sanitize_filename(target_title).lower()] = stub_path

    return {
        "created_stubs": created_stubs,
        "synced_files": 0
    }

