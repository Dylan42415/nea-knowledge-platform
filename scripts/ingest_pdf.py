"""CLI script to ingest a PDF into the vault."""

import argparse
import sys
import logging
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.pdf.classifier import classify_pdf
from src.ingestion.pdf.pymupdf_parser import extract_text
from src.ingestion.pdf.docling_parser import extract_with_layout
from src.ingestion.pdf.chunker import chunk_document
from src.extraction.concept_extractor import extract_concepts
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

        logger.info("Chunking data...")
        chunks = chunk_document(parsed_data)

        logger.info("Extracting concepts...")
        all_concepts = []
        
        # Batch chunk content into ~3000 character windows to optimize Gemini API calls
        batches = []
        current_batch = []
        current_len = 0
        for chunk in chunks:
            text_content = chunk.get("content", "") if isinstance(chunk, dict) else str(chunk)
            if not text_content:
                continue
            current_batch.append(text_content)
            current_len += len(text_content)
            if current_len >= 3000:
                batches.append("\n\n".join(current_batch))
                current_batch = []
                current_len = 0
        if current_batch:
            batches.append("\n\n".join(current_batch))

        for batch_text in batches:
            entities = extract_concepts(batch_text, source_context=file_path.name)
            for entity in entities:
                name = entity.get("name") if isinstance(entity, dict) else str(entity)
                if name and name not in all_concepts:
                    all_concepts.append(name)
                    e_type = entity.get("type", "concept") if isinstance(entity, dict) else "concept"
                    c_note = generate_note({
                        "title": name,
                        "summary": entity.get("description", f"Concept extracted from {file_path.name}") if isinstance(entity, dict) else "",
                        "source_file": file_path.name,
                        "source_format": "pdf"
                    }, e_type)
                    write_note(c_note, e_type, name, VAULT_ROOT)

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

        print(f"Successfully ingested {file_path.name} into vault.")
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

