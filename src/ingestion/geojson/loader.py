import json
from pathlib import Path
import geopandas as gpd

def load_geojson(file_path: Path) -> gpd.GeoDataFrame:
    """
    Load GeoJSON into a GeoDataFrame.
    Handle both .geojson and .json extensions.
    If CRS is missing, default to EPSG:4326 with a warning.
    """
    gdf = gpd.read_file(file_path)
    if gdf.crs is None:
        print(f"Warning: CRS missing in {file_path}, defaulting to EPSG:4326")
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf

def validate_geodata(gdf: gpd.GeoDataFrame) -> tuple[bool, list[str]]:
    """
    Check geometry validity, CRS presence, required properties.
    Return (is_valid, list_of_issues).
    """
    issues = []
    
    # Check valid geometry
    invalid_geoms = gdf[~gdf.geometry.is_valid]
    if not invalid_geoms.empty:
        issues.append(f"Found {len(invalid_geoms)} invalid geometries.")
        
    # Check CRS
    if gdf.crs is None:
        issues.append("CRS is missing.")
        
    is_valid = len(issues) == 0
    return is_valid, issues
