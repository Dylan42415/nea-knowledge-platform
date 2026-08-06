"""CLI script to ingest a PDF into the vault."""

import argparse
import sys
import logging
from pathlib import Path
import asyncio

from src.ingestion.pdf.classifier import classify_pdf
from src.ingestion.pdf.pymupdf_parser import extract_text
from src.ingestion.pdf.docling_parser import extract_with_layout
from src.ingestion.pdf.chunker import chunk_document
from src.extraction.concept_extractor import extract_concepts
from src.vault_writer.note_generator import generate_note, write_note, sanitize_filename
from src.vault_writer.linker import create_wikilinks, resolve_backlinks, update_links_in_note
from src.config import VAULT_ROOT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

async def main() -> None:
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
        if pdf_type == "text_heavy":
            parsed_data = extract_text(file_path)
        else:
            parsed_data = extract_with_layout(file_path)

        logger.info("Chunking data...")
        chunks = chunk_document(parsed_data)

        logger.info("Extracting concepts...")
        all_concepts = []
        for chunk in chunks:
            concepts = await extract_concepts(chunk)
            all_concepts.extend(concepts)

        logger.info("Writing vault notes...")
        note_data = {
            "title": file_path.name,
            "linked_concepts": all_concepts,
            "summary": f"Data ingested from {file_path.name}"
        }
        dataset_note_content = generate_note(note_data, "dataset")
        note_path = write_note(dataset_note_content, "dataset", file_path.name, VAULT_ROOT)
        # Note: In a real app we might update links in other notes, but for now we just log success.

        print(f"Successfully ingested {file_path.name} into vault.")
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
