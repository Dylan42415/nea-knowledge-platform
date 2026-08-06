"""CLI script to ingest a GeoJSON file into the vault."""

import argparse
import sys
import logging
from pathlib import Path
import asyncio

from src.ingestion.geojson.loader import GeoJSONLoader
from src.ingestion.geojson.feature_mapper import FeatureMapper
from src.extraction.concept_extractor import ConceptExtractor
from src.vault_writer.note_generator import NoteGenerator
from src.vault_writer.linker import Linker
from src.config import Config

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
    
    config = Config()
    loader = GeoJSONLoader()
    mapper = FeatureMapper()
    concept_extractor = ConceptExtractor()
    note_generator = NoteGenerator(config.obsidian_vault_dir)
    linker = Linker(config.obsidian_vault_dir)
    
    try:
        logger.info("Loading GeoJSON...")
        geojson_data = loader.load(file_path)
        
        logger.info("Validating GeoJSON...")
        if not loader.validate(geojson_data):
            logger.error("Invalid GeoJSON data.")
            sys.exit(1)

        logger.info("Mapping features...")
        features = mapper.map_features(geojson_data)

        logger.info("Extracting concepts and writing notes...")
        all_concepts = []
        for feature in features:
            desc = feature.get("description", "")
            concepts = await concept_extractor.extract(desc)
            all_concepts.extend(concepts)
            note_generator.create_location_note(feature, concepts)
            
        dataset_note = note_generator.create_dataset_note("geojson", file_path.name, all_concepts)
        linker.link_concepts(dataset_note, all_concepts)

        print(f"Successfully ingested {file_path.name} into vault.")
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
