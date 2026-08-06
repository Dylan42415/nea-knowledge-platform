"""
Automated Ontology & Knowledge Graph Refactoring Script.
Normalizes vault schemas, moves organization notes, merges duplicate concepts, and standardizes wikilinks.
"""
import os
import sys
import re
import yaml
from pathlib import Path

# Add project root to sys.path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.config import VAULT_ROOT

vault_root = Path(VAULT_ROOT)

def run_ontology_fix():
    print("=== Starting Knowledge Graph Ontology Normalization ===")
    
    # 1. Delete numeric placeholder files (e.g. 1.md, 6.md, 14.md, etc.)
    for f in list(vault_root.rglob("*.md")):
        if f.stem.isdigit():
            print(f"Purging numeric placeholder file: {f.relative_to(vault_root)}")
            f.unlink()

    # 2. Define Canonical Merge Targets
    merges = [
        ("biochemical_oxygen_demand.md", "biochemical_oxygen_demand_bod.md", "Biochemical Oxygen Demand (BOD)", ["Biochemical Oxygen Demand", "BOD"]),
        ("dissolved_oxygen.md", "dissolved_oxygen_do.md", "Dissolved Oxygen (DO)", ["Dissolved Oxygen", "DO"]),
        ("total_suspended_solids.md", "total_suspended_solids_tss.md", "Total Suspended Solids (TSS)", ["Total Suspended Solids", "TSS"]),
        ("national_environment_agency.md", "national_environment_agency_nea.md", "National Environment Agency (NEA)", ["National Environment Agency", "NEA"]),
    ]

    for source_name, target_name, canonical_title, aliases in merges:
        source_files = list(vault_root.rglob(source_name))
        target_files = list(vault_root.rglob(target_name))

        if source_files and target_files:
            s_file = source_files[0]
            t_file = target_files[0]
            if s_file != t_file and s_file.exists() and t_file.exists():
                print(f"Merging {s_file.name} into canonical note {t_file.name}...")
                s_content = s_file.read_text(encoding='utf-8')
                t_content = t_file.read_text(encoding='utf-8')
                
                # Append key findings if unique
                if "## Key Data / Findings" in s_content and "### Additional Findings" not in t_content:
                    s_findings = s_content.split("## Key Data / Findings", 1)[-1].split("## Relationships", 1)[0].strip()
                    if s_findings and s_findings not in t_content:
                        t_content += f"\n\n### Additional Findings ({s_file.stem})\n\n{s_findings}\n"
                
                t_file.write_text(t_content, encoding='utf-8')
                s_file.unlink()
                print(f"Deleted duplicate note: {s_file.name}")

    # 3. Move Organization Notes to vault/organizations/ and Update Frontmatter
    org_stems = [
        "national_environment_agency_nea", "pub", "crisp", "mss",
        "ministry_of_health_moh", "national_environment_agency"
    ]

    orgs_dir = vault_root / "organizations"
    orgs_dir.mkdir(parents=True, exist_ok=True)

    for f in list(vault_root.rglob("*.md")):
        if f.stem in org_stems and f.parent.name != "organizations":
            target_path = orgs_dir / f.name
            print(f"Moving organization note {f.name} -> vault/organizations/")
            content = f.read_text(encoding='utf-8')
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    meta = yaml.safe_load(parts[1]) or {}
                    meta["type"] = "Organization"
                    new_fm = yaml.dump(meta, sort_keys=False).strip()
                    content = f"---\n{new_fm}\n---" + parts[2]
            f.write_text(content, encoding='utf-8')
            if f != target_path:
                os.replace(f, target_path)

    # 4. Standardize Wikilinks & Relationship Predicates across ALL Vault Notes
    replacements = {
        "[[Biochemical Oxygen Demand]]": "[[Biochemical Oxygen Demand (BOD)]]",
        "[[Dissolved Oxygen]]": "[[Dissolved Oxygen (DO)]]",
        "[[Total Suspended Solids]]": "[[Total Suspended Solids (TSS)]]",
        "[[National Environment Agency]]": "[[National Environment Agency (NEA)]]",
        "[[MOH]]": "[[Ministry of Health (MOH)]]",
        "[[PUB]]": "[[PUB (Public Utilities Board)]]",
    }

    predicate_standardization = {
        "MONITORED_BY": "MANAGED_BY",
        "COLLABORATED_WITH": "MANAGED_BY",
        "PART_OF": "LOCATED_IN",
    }

    for f in list(vault_root.rglob("*.md")):
        content = f.read_text(encoding='utf-8')
        modified = False

        # Replace duplicate wikilinks
        for old_link, new_link in replacements.items():
            if old_link in content:
                content = content.replace(old_link, new_link)
                modified = True

        # Replace un-canonical predicates
        for old_p, new_p in predicate_standardization.items():
            if f"- **{old_p}**" in content:
                content = content.replace(f"- **{old_p}**", f"- **{new_p}**")
                modified = True

        # Ensure frontmatter type for concepts
        if f.parent.name == "concepts" and content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                meta = yaml.safe_load(parts[1]) or {}
                if meta.get("type", "").lower() != "concept":
                    meta["type"] = "Concept"
                    new_fm = yaml.dump(meta, sort_keys=False).strip()
                    content = f"---\n{new_fm}\n---" + parts[2]
                    modified = True

        if modified:
            f.write_text(content, encoding='utf-8')

    print("=== Knowledge Graph Ontology Normalization Complete! ===")

if __name__ == "__main__":
    run_ontology_fix()
