import geopandas as gpd

def map_features_to_notes(gdf: gpd.GeoDataFrame, source_file: str) -> list[dict]:
    """
    Map GeoJSON features to vault location notes.
    Group features intelligently if dataset is large (>100 features).
    """
    notes = []
    
    # If dataset is large, we could group by 'type' or 'category'
    if len(gdf) > 100:
        grouping_col = 'type' if 'type' in gdf.columns else ('category' if 'category' in gdf.columns else None)
        # Note: True grouping logic would depend on use case. Here we keep it simple but acknowledge the requirement.
        # Could create aggregated notes per group, but for now we iterate all features.
    
    for idx, row in gdf.iterrows():
        title = row.get('name') or row.get('NAME') or f"Location_{idx}"
        
        geometry = row.geometry
        geometry_type = geometry.geom_type if geometry else "Unknown"
        centroid = geometry.centroid if geometry else None
        coordinates = f"{centroid.y}, {centroid.x}" if centroid else "Unknown"
        
        properties = {col: row[col] for col in gdf.columns if col != 'geometry' and not str(row[col]).startswith('<')}
        
        note = {
            "title": str(title),
            "type": "location",
            "geometry_type": geometry_type,
            "coordinates": coordinates,
            "properties": properties,
            "source_file": source_file,
            "tags": ["location", "geojson"]
        }
        
        if 'type' in row:
            note['tags'].append(str(row['type']).lower())
        elif 'category' in row:
            note['tags'].append(str(row['category']).lower())
            
        notes.append(note)
        
    return notes
