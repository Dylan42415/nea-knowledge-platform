import os
import sys
import json
import streamlit as st
import pydeck as pdk
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import PROJECT_ROOT

def render_map_page():
    """Renders the interactive map view with GeoJSON layers."""
    st.title("🗺️ Map View")
    
    # Search multiple potential directories for GeoJSON files
    search_dirs = [
        os.path.join(PROJECT_ROOT, 'data', 'geojson'),
        os.path.join(PROJECT_ROOT, 'tests', 'fixtures')
    ]
    
    file_map = {}
    for s_dir in search_dirs:
        if os.path.exists(s_dir):
            for f in os.listdir(s_dir):
                if f.endswith('.geojson') or f.endswith('.json'):
                    file_map[f] = os.path.join(s_dir, f)
                    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Layers")
        active_layers = []
        if file_map:
            for f_name in file_map.keys():
                if st.checkbox(f_name, value=True):
                    active_layers.append(f_name)
        else:
            st.info("No GeoJSON data found. Add data to data/geojson/")
            
    with col2:
        layers = []
        # Colors for different datasets (placeholder logic)
        colors = [
            [0, 128, 255],
            [255, 0, 128],
            [128, 255, 0],
            [255, 128, 0]
        ]
        
        for idx, filename in enumerate(active_layers):
            filepath = file_map[filename]
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    
                color = colors[idx % len(colors)]
                
                layer = pdk.Layer(
                    "GeoJsonLayer",
                    data,
                    opacity=0.8,
                    stroked=False,
                    filled=True,
                    extruded=True,
                    wireframe=True,
                    get_elevation="properties.elevation || 10",
                    get_fill_color=color + [150],
                    get_line_color=[255, 255, 255],
                    pickable=True,
                )
                layers.append(layer)
            except Exception as e:
                st.error(f"Failed to load {filename}: {e}")
                
        # Centered on Singapore
        view_state = pdk.ViewState(
            latitude=1.3521,
            longitude=103.8198,
            zoom=11,
            pitch=45,
            bearing=0
        )
        
        r = pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            tooltip={"html": "<b>{name}</b><br/>{description}", "style": {"color": "white"}},
            map_style=pdk.map_styles.DARK
        )
        
        st.pydeck_chart(r)
        
        if not layers:
            st.markdown(
                "<div style='text-align: center; padding: 2rem; background: rgba(255,255,255,0.05); border-radius: 8px; margin-top: 1rem;'>"
                "Select layers from the sidebar to view data on the map."
                "</div>", 
                unsafe_allow_html=True
            )
