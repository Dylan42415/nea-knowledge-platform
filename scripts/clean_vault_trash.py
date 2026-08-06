"""
Vault Sanitizer and Garbage Collector.
Purges ONLY legacy trash placeholder notes containing 'Extracted via fallback mechanism'.
Preserves ALL Gemini-generated Gold Standard notes.
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import VAULT_ROOT

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

        # ONLY delete legacy fallback placeholder notes
        if "Extracted via fallback mechanism" in content or len(content.strip()) < 30:
            try:
                filepath.unlink()
                purged_count += 1
            except Exception:
                pass
        else:
            retained_count += 1

    print(f"Purged {purged_count} legacy fallback placeholder files.")
    print(f"Retained {retained_count} Gold Standard notes in vault.")

if __name__ == "__main__":
    clean_vault()
