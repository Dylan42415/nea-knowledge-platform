"""CLI script to ingest a GeoJSON file into the vault."""

import argparse
import sys
import logging
from pathlib import Path
import asyncio

from src.ingestion.geojson.loader import load_geojson, validate_geodata
from src.ingestion.geojson.feature_mapper import map_features_to_notes
from src.extraction.concept_extractor import extract_concepts
from src.vault_writer.note_generator import generate_note, write_note, sanitize_filename
from src.vault_writer.linker import create_wikilinks, resolve_backlinks, update_links_in_note
from src.config import VAULT_ROOT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a GeoJSON file into the NEA Knowledge Platform vault.")
    parser.add_argument("file_path", type=str, help="Path to the GeoJSON file to ingest")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    file_path = Path(args.file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    logger.info(f"Ingesting GeoJSON: {file_path}")
    
    try:
        logger.info("Loading GeoJSON...")
        geojson_data = load_geojson(file_path)
        
        logger.info("Validating GeoJSON...")
        is_valid, issues = validate_geodata(geojson_data)
        if not is_valid:
            logger.error(f"Invalid GeoJSON data: {issues}")
            sys.exit(1)

        logger.info("Mapping features...")
        features = map_features_to_notes(geojson_data)

        logger.info("Extracting concepts and writing notes...")
        all_concepts = []
        for feature in features:
            desc = feature.get("description", "")
            concepts = await extract_concepts(desc)
            all_concepts.extend(concepts)
            note_content = generate_note(feature, "location")
            write_note(note_content, "location", feature.get("title", "location"), VAULT_ROOT)
            
        note_data = {
            "title": file_path.name,
            "linked_concepts": all_concepts,
            "summary": f"Dataset ingested from GeoJSON {file_path.name}"
        }
        dataset_note_content = generate_note(note_data, "dataset")
        write_note(dataset_note_content, "dataset", file_path.name, VAULT_ROOT)

        print(f"Successfully ingested {file_path.name} into vault.")
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
