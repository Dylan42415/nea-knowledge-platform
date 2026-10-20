import re
from pathlib import Path
from datetime import datetime, timezone
import yaml

def sanitize_filename(name: str) -> str:
    """
    Sanitize filename for Obsidian Wikilink resolution compatibility.
    Strips illegal Windows path characters (\\ / : * ? " < > |) while preserving
    exact title case and spaces so [[Title]] resolves directly to Title.md.
    """
    safe_name = re.sub(r'[\\/:*?"<>|]', '', name).strip()
    return safe_name if safe_name else "Untitled"


def generate_note(note_data: dict, note_type: str) -> str:
    """
    Generate complete Gold Standard Markdown with YAML frontmatter, 
    data tables, typed relationships, and source citations matching gold_standard_example.md.
    """
    title = note_data.get("title", "Untitled")
    # Clean up extension if present in title
    if title.lower().endswith(".pdf") or title.lower().endswith(".geojson") or title.lower().endswith(".json"):
        title = Path(title).stem.replace("_", " ").title()

    frontmatter = {
        "title": title,
        "type": note_type.capitalize(),
        "source_document": note_data.get("source_document") or note_data.get("source_file", ""),
        "source_location": note_data.get("source_location", ""),
        "extraction_date": note_data.get("extraction_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "tags": note_data.get("tags", [])
    }
    
    # Add extra properties
    for k, v in note_data.get("properties", {}).items():
        if k not in frontmatter:
            frontmatter[k] = v
            
    if note_type.lower() == "location":
        if note_data.get("geometry_type"):
            frontmatter["geometry_type"] = note_data.get("geometry_type")
        if note_data.get("coordinates"):
            frontmatter["coordinates"] = note_data.get("coordinates")
        
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    
    sections = [f"# {title}\n"]
    
    # Summary section
    summary = note_data.get("summary", "No summary available.")
    sections.append(f"## Summary\n{summary}")
    
    # Key Data / Findings section (Markdown tables / thresholds)
    key_data = note_data.get("key_data", "")
    if key_data and key_data.strip():
        sections.append(f"## Key Data / Findings\n\n{key_data.strip()}")
        
    # Relationships section (Typed relationships or wikilink lists)
    relationships = note_data.get("relationships", [])
    linked_concepts = note_data.get("linked_concepts", [])
    
    if relationships and isinstance(relationships, list):
        rel_text = "## Relationships\n"
        for rel in relationships:
            if isinstance(rel, dict):
                pred = rel.get("predicate", "RELATED_TO").upper()
                target = rel.get("target", "")
                if target:
                    rel_text += f"- **{pred}** → [[{target}]]\n"
        sections.append(rel_text.strip())
    elif linked_concepts:
        rel_text = "## Related\n"
        for concept in linked_concepts:
            c_name = concept.get("name", str(concept)) if isinstance(concept, dict) else str(concept)
            rel_text += f"- [[{c_name}]]\n"
        sections.append(rel_text.strip())
        
    # Knowledge Gaps & Unresolved Blindspots section ("Hole Finder")
    knowledge_gaps = note_data.get("knowledge_gaps", [])
    if knowledge_gaps and isinstance(knowledge_gaps, list):
        gap_lines = []
        for gap in knowledge_gaps:
            if isinstance(gap, str) and gap.strip():
                gap_lines.append(f"- ⚠️ {gap.strip()}")
        if gap_lines:
            sections.append("## Knowledge Gaps & Unresolved Blindspots\n" + "\n".join(gap_lines))
            frontmatter["knowledge_gaps"] = [str(g) for g in knowledge_gaps if g]

    # Source Excerpt section
    excerpt = note_data.get("excerpt", "")
    if excerpt and excerpt.strip():
        source_doc = frontmatter.get("source_document", "")
        source_loc = frontmatter.get("source_location", "")
        citation = f" — {source_doc}"
        if source_loc:
            citation += f", {source_loc}"
        quote_text = "\n".join(f"> {line}" for line in excerpt.strip().splitlines())
        sections.append(f"## Source Excerpt\n{quote_text}\n{citation}")

    # Re-dump YAML if knowledge_gaps was added to frontmatter
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

    note_body = "\n\n".join(sections)
    return f"---\n{yaml_str}---\n\n{note_body}\n"

def calculate_data_density(content: str) -> int:
    """
    Calculates information density score based on markdown tables, numerical metrics with units,
    and typed wikilinks.
    """
    table_rows = len([line for line in content.splitlines() if "|" in line])
    metrics = len(re.findall(r'\b\d+(?:\.\d+)?\s*(?:ppb|µg/m³|mg/l|mg/Nm³|%|counts/100\s*ml)\b', content, re.IGNORECASE))
    wikilinks = len(re.findall(r'\[\[(.*?)\]\]', content))
    return (table_rows * 10) + (metrics * 5) + (wikilinks * 2) + (len(content.strip()) // 100)

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
    
    sub_dir = type_to_dir.get(note_type.lower(), "concepts")
    target_dir = vault_root / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    
    safe_filename = sanitize_filename(filename) + ".md"
    file_path = target_dir / safe_filename
    
    if file_path.exists() and note_type.lower() != "dataset":
        try:
            existing_content = file_path.read_text(encoding='utf-8')
            new_density = calculate_data_density(note_content)
            old_density = calculate_data_density(existing_content)

            # If new note has higher informational density, overwrite with higher density note
            if new_density > old_density:
                file_path.write_text(note_content, encoding='utf-8')
                return file_path
            elif "## Key Data / Findings" in note_content:
                new_key_data = note_content.split("## Key Data / Findings", 1)[-1].split("## Relationships", 1)[0].strip()
                if new_key_data and new_key_data not in existing_content:
                    existing_content += f"\n\n### Additional Findings ({filename})\n\n{new_key_data}\n"
                    file_path.write_text(existing_content, encoding='utf-8')
                    return file_path
                return file_path
            else:
                return file_path
        except Exception:
            pass

    file_path.write_text(note_content, encoding='utf-8')
    
    # Auto-generate stub files for any missing [[Wikilink]] target entities
    try:
        wikilinks = re.findall(r'\[\[(.*?)\]\]', note_content)
        existing_stems = {f.stem.lower() for f in vault_root.rglob('*.md')}
        concepts_dir = vault_root / "concepts"
        concepts_dir.mkdir(parents=True, exist_ok=True)
        
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for link in wikilinks:
            target_title = link.split('|')[0].strip()
            if not target_title:
                continue
            target_sanitized = sanitize_filename(target_title)
            if target_title.lower() not in existing_stems and target_sanitized not in existing_stems:
                stub_path = concepts_dir / f"{target_sanitized}.md"
                if not stub_path.exists():
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
{target_title} is a recognized environmental concept, statutory benchmark, or organizational entity linked within the NEA Knowledge Graph.

## Related References
- Linked from [[{filename.replace('.md', '')}]]
"""
                    stub_path.write_text(stub_content, encoding='utf-8')
                    existing_stems.add(target_sanitized)
    except Exception:
        pass

    return file_path

