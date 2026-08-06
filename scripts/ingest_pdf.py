"""CLI script to ingest a PDF into the vault with Gold Standard Wiki Extraction."""

import argparse
import sys
import time
import logging
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.pdf.classifier import classify_pdf
from src.ingestion.pdf.pymupdf_parser import extract_text
from src.ingestion.pdf.docling_parser import extract_with_layout
from src.extraction.topic_aggregator import aggregate_topics_from_document
from src.extraction.gold_extractor import extract_gold_notes
from src.vault_writer.note_generator import generate_note, write_note
from src.config import VAULT_ROOT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a PDF file into the NEA Knowledge Platform vault.")
    parser.add_argument("file_path", type=str, help="Path to the PDF file to ingest")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    file_path = Path(args.file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    logger.info(f"Ingesting PDF: {file_path}")
    
    try:
        logger.info("Classifying PDF...")
        pdf_type = classify_pdf(file_path)
        logger.debug(f"Classification result: {pdf_type}")

        logger.info("Parsing PDF...")
        if pdf_type == "text":
            parsed_data = extract_text(file_path)
        else:
            parsed_data = extract_with_layout(file_path)

        logger.info("Aggregating document topics...")
        topic_payloads = aggregate_topics_from_document(parsed_data, doc_filename=file_path.name)
        logger.info(f"Aggregated {len(topic_payloads)} topic payloads.")

        all_concepts = []
        
        for payload in topic_payloads:
            logger.info(f"Extracting Gold Standard note for: {payload.get('title')}")
            gold_notes = extract_gold_notes(payload)
            
            for note_dict in gold_notes:
                name = note_dict.get("title", "Untitled").strip()
                if not name:
                    continue
                if name not in all_concepts:
                    all_concepts.append(name)
                
                n_type = note_dict.get("type", "Concept")
                note_content = generate_note(note_dict, n_type)
                write_note(note_content, n_type, name, VAULT_ROOT)

            # 1-second pace delay to prevent 429 quota spikes
            time.sleep(1)

        logger.info("Writing dataset note...")
        note_data = {
            "title": file_path.name,
            "source_file": file_path.name,
            "source_format": "pdf",
            "linked_concepts": all_concepts,
            "summary": f"Dataset ingested from PDF {file_path.name}"
        }
        dataset_note_content = generate_note(note_data, "dataset")
        write_note(dataset_note_content, "dataset", file_path.name, VAULT_ROOT)

        print(f"Successfully ingested {file_path.name} into vault with Gold Standard Wiki Extraction.")
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
