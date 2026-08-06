"""Tests for GeoJSON loader and feature mapper."""

import pytest
from pathlib import Path
from src.ingestion.geojson.loader import load_geojson, validate_geodata
from src.ingestion.geojson.feature_mapper import map_features_to_notes

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample.geojson"

def test_load_geojson():
    """Test loading a GeoJSON file."""
    gdf = load_geojson(FIXTURE_PATH)
    assert not gdf.empty
    assert len(gdf) == 3

def test_validate_geodata():
    """Test validation of valid GeoJSON data."""
    gdf = load_geojson(FIXTURE_PATH)
    is_valid, errors = validate_geodata(gdf)
    assert is_valid is True
    assert len(errors) == 0

def test_feature_mapper():
    """Test mapping GeoJSON features to dictionaries."""
    gdf = load_geojson(FIXTURE_PATH)
    notes = map_features_to_notes(gdf, source_file="sample.geojson")
    
    assert len(notes) == 3
    assert notes[0]["title"] == "Marina Bay"
    assert notes[0]["type"] == "location"
    assert "iconic bay area" in str(notes[0].get("properties", {})).lower()
    assert isinstance(notes[0]["coordinates"], str)
