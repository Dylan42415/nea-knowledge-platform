"""
Gold Standard Vault Re-Ingestion Engine for soe_report.pdf.
Populates ObsidianVault/vault/ with 100% Gold Standard Markdown notes.
"""
import sys
import time
import logging
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.pdf.pymupdf_parser import extract_text
from src.extraction.topic_aggregator import aggregate_topics_from_document
from src.extraction.gold_extractor import extract_gold_notes
from src.vault_writer.note_generator import generate_note, write_note
from src.config import VAULT_ROOT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PDF_PATH = Path(r"C:\Users\Dfault\Downloads\OneDrive_1_01-08-2026 (1)\Publications\soe_report.pdf")
def main():
    if not PDF_PATH.exists():
        logger.error(f"PDF not found: {PDF_PATH}")
        sys.exit(1)

    logger.info("Cleaning stale markdown files from vault subdirectories...")
    for sub in ["concepts", "datasets", "locations", "organizations"]:
        sub_dir = VAULT_ROOT / sub
        if sub_dir.exists():
            for f in sub_dir.glob("*.md"):
                try:
                    f.unlink()
                except Exception:
                    pass

    logger.info(f"Parsing PDF text from: {PDF_PATH.name}")
    parsed_doc = extract_text(PDF_PATH)
    
    logger.info("Aggregating document topic windows...")
    payloads = aggregate_topics_from_document(parsed_doc, doc_filename=PDF_PATH.name)
    logger.info(f"Generated {len(payloads)} topic windows.")

    ingested_count = 0
    all_concept_names = []

    for i, payload in enumerate(payloads, 1):
        logger.info(f"[{i}/{len(payloads)}] Extracting Gold Standard note for: {payload.get('source_location')}")
        gold_notes = extract_gold_notes(payload)

        for note_dict in gold_notes:
            name = note_dict.get("title", "").strip()
            if not name or name == "Untitled":
                continue

            all_concept_names.append(name)
            note_type = note_dict.get("type", "Concept")
            note_content = generate_note(note_dict, note_type)
            written_path = write_note(note_content, note_type, name, VAULT_ROOT)
            logger.info(f" -> Wrote Gold Note: {written_path.name}")
            ingested_count += 1

        # 1.5-second pacing delay to respect API rate limits
        time.sleep(1.5)

    # Write Dataset Note for soe_report.pdf
    ds_note_data = {
        "title": PDF_PATH.name,
        "source_file": PDF_PATH.name,
        "source_format": "pdf",
        "linked_concepts": all_concept_names,
        "summary": "Official Singapore State of the Environment (SOE) Report detailing air quality, water quality, waste management, public health, and climate initiatives."
    }
    ds_content = generate_note(ds_note_data, "dataset")
    write_note(ds_content, "dataset", PDF_PATH.name, VAULT_ROOT)

    logger.info(f"COMPLETED! Re-ingested {ingested_count} Gold Standard notes into vault.")

if __name__ == "__main__":
    main()
