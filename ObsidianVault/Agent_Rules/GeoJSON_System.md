# GeoJSON System

## Library choices
- **leafmap** (primary) — Streamlit-native, wraps folium/ipyleaflet/pydeck/
  kepler.gl backends, reads GeoJSON/Shapefile/GeoPackage directly via
  GeoPandas.
- **pydeck** — used directly (via `st.pydeck_chart`) where 3D/large-layer
  rendering is needed.

Alternatives considered (streamlit-folium, raw folium) are logged in
`Decision_Log.md`.

## Pipeline stages
1. **Load** — read GeoJSON into a GeoDataFrame.
2. **Validate** — check geometry validity, CRS, required properties.
3. **Feature → note** — each feature (or feature group, for large datasets)
   becomes a `locations/` vault note with its properties as frontmatter and
   a link back to the source dataset note.
4. **Layer registration** — the Streamlit map view registers the dataset as
   a togglable layer.

## Performance note
If deployed on Streamlit Community Cloud, the 1GB RAM ceiling means large
NEA geo datasets (e.g. high-resolution sensor networks) need simplification
or tiling before rendering — not loaded raw into the map component.

## Map view in the app
The Streamlit app's map view lets a user toggle dataset layers on/off and
click a feature to jump to its vault note (and from there, into the linked
concept/dataset graph).
