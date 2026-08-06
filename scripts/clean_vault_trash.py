"""
Vault Sanitizer and Garbage Collector.
Purges trash placeholder notes created by legacy regex extractors.
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import VAULT_ROOT

VALID_POLLUTANTS_AND_TOPICS = {
    "pollutant_standards_index", "psi", "benzene", "pm25", "pm10", 
    "particulate_matter", "sulphur_dioxide", "so2", "nitrogen_dioxide", "no2", 
    "carbon_monoxide", "co", "ozone", "o3", "lead", "dioxins", "enterococcus", 
    "dissolved_oxygen", "do", "total_suspended_solids", "tss", "biochemical_oxygen_demand", 
    "bod", "microplastics", "marine_litter", "bswi", "ves", "covid_19", "circuit_breaker",
    "national_environment_agency", "nea", "emmd", "who_air_quality_guidelines",
    "singapore_ambient_air_quality", "coastal_waters", "recreational_beaches",
    "maritime_singapore_decarbonisation_blueprint_2050", "greenhouse_gas",
    "emerging_contaminants", "pfas", "antimicrobial_resistance", "haze_monitoring",
    "low_cost_air_quality_sensors", "neri", "soe_reportpdf"
}

def clean_vault():
    vault_dir = Path(VAULT_ROOT)
    if not vault_dir.exists():
        print("Vault root does not exist.")
        return

    purged_count = 0
    retained_count = 0

    for filepath in vault_dir.rglob("*.md"):
        if filepath.name.startswith(".") or filepath.name == ".gitkeep":
            continue

        content = filepath.read_text(encoding="utf-8")
        stem = filepath.stem.lower()

        # Check if file is trash
        is_trash = False
        if "Extracted via fallback mechanism" in content:
            is_trash = True
        elif len(content) < 300 and "## Key Data" not in content and not any(k in stem for k in VALID_POLLUTANTS_AND_TOPICS):
            is_trash = True

        if is_trash:
            try:
                filepath.unlink()
                purged_count += 1
            except Exception:
                pass
        else:
            retained_count += 1

    print(f"Purged {purged_count} trash placeholder files.")
    print(f"Retained {retained_count} Gold Standard notes in vault.")

if __name__ == "__main__":
    clean_vault()
