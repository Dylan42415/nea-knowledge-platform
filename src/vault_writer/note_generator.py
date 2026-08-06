import re
from pathlib import Path
from datetime import datetime, timezone
import yaml

def sanitize_filename(name: str) -> str:
    """
    Convert to snake_case, remove special chars.
    """
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '_', name)
    return name.lower()

def generate_note(note_data: dict, note_type: str) -> str:
    """
    Generate complete markdown with YAML frontmatter and body.
    """
    frontmatter = {
        "title": note_data.get("title", "Untitled"),
        "type": note_type,
        "source_file": note_data.get("source_file", ""),
        "source_format": note_data.get("source_format", "unknown"),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "tags": note_data.get("tags", [])
    }
    
    # Add extra props
    for k, v in note_data.get("properties", {}).items():
        if k not in frontmatter:
            frontmatter[k] = v
            
    if note_type == "location":
        frontmatter["geometry_type"] = note_data.get("geometry_type")
        frontmatter["coordinates"] = note_data.get("coordinates")
        
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    
    body = note_data.get("summary", "No summary available.")
    
    # Create wikilinks
    linked_concepts = note_data.get("linked_concepts", [])
    if linked_concepts:
        body += "\n\n## Related\n"
        for concept in linked_concepts:
            if isinstance(concept, dict):
                c_name = concept.get("name", str(concept))
            else:
                c_name = str(concept)
            body += f"- [[{c_name}]]\n"
            
    note_content = f"---\n{yaml_str}---\n\n{body}\n"
    return note_content

def write_note(note_content: str, note_type: str, filename: str, vault_root: Path) -> Path:
    """
    Write to the appropriate subdirectory (datasets/, concepts/, locations/, organizations/)
    """
    type_to_dir = {
        "dataset": "datasets",
        "concept": "concepts",
        "location": "locations",
        "organization": "organizations"
    }
    
    sub_dir = type_to_dir.get(note_type, "misc")
    target_dir = vault_root / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    
    safe_filename = sanitize_filename(filename) + ".md"
    file_path = target_dir / safe_filename
    
    file_path.write_text(note_content, encoding='utf-8')
    return file_path
