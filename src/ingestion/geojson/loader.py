import json
import logging
from pathlib import Path
import geopandas as gpd

logger = logging.getLogger(__name__)

def load_geojson(file_path: Path) -> gpd.GeoDataFrame:
    """
    Load GeoJSON into a GeoDataFrame.
    Handle both .geojson and .json extensions.
    If CRS is missing, default to EPSG:4326 with a warning.
    """
    try:
        gdf = gpd.read_file(file_path)
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise
        
    if gdf.crs is None:
        logger.warning(f"CRS missing in {file_path}, defaulting to EPSG:4326")
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf

def validate_geodata(gdf: gpd.GeoDataFrame) -> tuple[bool, list[str]]:
    """
    Check geometry validity, CRS presence, required properties.
    Return (is_valid, list_of_issues).
    """
    issues = []
    
    if "geometry" not in gdf.columns or gdf.geometry is None:
        issues.append("No geometry column found.")
    else:
        # Check valid geometry
        invalid_geoms = gdf[~gdf.geometry.is_valid]
        if not invalid_geoms.empty:
            issues.append(f"Found {len(invalid_geoms)} invalid geometries.")
            
    # Check CRS
    if getattr(gdf, "crs", None) is None:
        issues.append("CRS is missing.")
        
    is_valid = len(issues) == 0
    return is_valid, issues
