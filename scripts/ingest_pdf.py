"""CLI script to ingest a PDF into the vault."""

import argparse
import sys
import logging
from pathlib import Path
import asyncio

from src.ingestion.pdf.classifier import PDFClassifier
from src.ingestion.pdf.pymupdf_parser import PyMuPDFParser
from src.ingestion.pdf.docling_parser import DoclingParser
from src.ingestion.pdf.chunker import PDFChunker
from src.extraction.concept_extractor import ConceptExtractor
from src.vault_writer.note_generator import NoteGenerator
from src.vault_writer.linker import Linker
from src.config import Config

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
    
    config = Config()
    classifier = PDFClassifier()
    chunker = PDFChunker()
    concept_extractor = ConceptExtractor()
    note_generator = NoteGenerator(config.obsidian_vault_dir)
    linker = Linker(config.obsidian_vault_dir)
    
    try:
        logger.info("Classifying PDF...")
        pdf_type = classifier.classify(file_path)
        logger.debug(f"Classification result: {pdf_type}")

        logger.info("Parsing PDF...")
        if pdf_type == "text_heavy":
            parser_instance = PyMuPDFParser()
        else:
            parser_instance = DoclingParser()
        
        parsed_data = parser_instance.parse(file_path)

        logger.info("Chunking data...")
        chunks = chunker.chunk(parsed_data)

        logger.info("Extracting concepts...")
        all_concepts = []
        for chunk in chunks:
            concepts = await concept_extractor.extract(chunk)
            all_concepts.extend(concepts)

        logger.info("Writing vault notes...")
        dataset_note = note_generator.create_dataset_note("pdf", file_path.name, all_concepts)
        linker.link_concepts(dataset_note, all_concepts)

        print(f"Successfully ingested {file_path.name} into vault.")
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
