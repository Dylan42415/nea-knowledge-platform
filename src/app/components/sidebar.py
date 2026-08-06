import os
import tempfile
import sys
from pathlib import Path
import streamlit as st

# Ensure project root is in sys.path
_current = Path(__file__).resolve()
for _p in [_current] + list(_current.parents):
    if (_p / "src").is_dir():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

from src.config import VAULT_ROOT, PROJECT_ROOT
from src.ingestion.pdf.classifier import classify_pdf
from src.ingestion.pdf.pymupdf_parser import extract_text
from src.ingestion.pdf.docling_parser import extract_with_layout
from src.ingestion.pdf.chunker import chunk_document
from src.ingestion.geojson.loader import load_geojson, validate_geodata
from src.ingestion.geojson.feature_mapper import map_features_to_notes
from src.extraction.concept_extractor import extract_concepts
from src.vault_writer.note_generator import generate_note, write_note

def render_sidebar() -> str:
    """
    Renders the sidebar with navigation, stats, and an ingestion section.
    
    Returns:
        str: The selected navigation option.
    """
    vault_dir = Path(VAULT_ROOT)
    
    # Calculate real vault stats
    doc_count = len(list((vault_dir / "datasets").rglob("*.md"))) if (vault_dir / "datasets").exists() else 0
    concept_count = len(list((vault_dir / "concepts").rglob("*.md"))) if (vault_dir / "concepts").exists() else 0
    location_count = len(list((vault_dir / "locations").rglob("*.md"))) if (vault_dir / "locations").exists() else 0
    org_count = len(list((vault_dir / "organizations").rglob("*.md"))) if (vault_dir / "organizations").exists() else 0
    
    with st.sidebar:
        st.title("🌏 NEA Platform")
        
        st.markdown("---")
        st.subheader("Navigation")
        # Navigation radio
        selected_page = st.radio(
            "Go to",
            ['Dashboard', 'Browse Notes', 'Map View', 'Knowledge Graph', 'Chat with Vault'],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.subheader("Platform Stats")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Datasets", value=str(doc_count))
            st.metric(label="Concepts", value=str(concept_count))
        with col2:
            st.metric(label="Locations", value=str(location_count))
            st.metric(label="Organizations", value=str(org_count))
            
        st.markdown("---")
        st.subheader("Ingest New Data")
        uploaded_file = st.file_uploader("Upload PDF or GeoJSON", type=["pdf", "geojson", "json"])
        if uploaded_file is not None:
            if st.button("Process Ingestion", type="primary"):
                with st.spinner(f"Ingesting {uploaded_file.name}..."):
                    try:
                        ext = Path(uploaded_file.name).suffix.lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = Path(tmp.name)
                            
                        if ext == ".pdf":
                            pdf_type = classify_pdf(tmp_path)
                            parsed = extract_text(tmp_path) if pdf_type == "text" else extract_with_layout(tmp_path)
                            chunks = chunk_document(parsed)
                            all_c = []
                            for chunk in chunks:
                                text_content = chunk.get("content", "") if isinstance(chunk, dict) else str(chunk)
                                if text_content:
                                    entities = extract_concepts(text_content, source_context=uploaded_file.name)
                                    for e in entities:
                                        name = e.get("name") if isinstance(e, dict) else str(e)
                                        if name and name not in all_c:
                                            all_c.append(name)
                                            e_type = e.get("type", "concept") if isinstance(e, dict) else "concept"
                                            c_note_data = {
                                                "title": name,
                                                "summary": e.get("summary") or e.get("description", f"Concept extracted from {uploaded_file.name}") if isinstance(e, dict) else "",
                                                "source_document": uploaded_file.name,
                                                "source_location": e.get("source_location", "") if isinstance(e, dict) else "",
                                                "key_data": e.get("key_data", "") if isinstance(e, dict) else "",
                                                "relationships": e.get("relationships", []) if isinstance(e, dict) else [],
                                                "excerpt": e.get("excerpt", "") if isinstance(e, dict) else ""
                                            }
                                            cnote = generate_note(c_note_data, e_type)
                                            write_note(cnote, e_type, name, VAULT_ROOT)
                            ds_note = generate_note({
                                "title": uploaded_file.name,
                                "source_file": uploaded_file.name,
                                "source_format": "pdf",
                                "linked_concepts": all_c,
                                "summary": f"Dataset ingested from {uploaded_file.name}"
                            }, "dataset")
                            write_note(ds_note, "dataset", uploaded_file.name, VAULT_ROOT)
                            
                        elif ext in [".geojson", ".json"]:
                            gdf = load_geojson(tmp_path)
                            is_valid, issues = validate_geodata(gdf)
                            if not is_valid:
                                st.error(f"GeoJSON validation failed: {issues}")
                                os.unlink(tmp_path)
                                return selected_page
                                
                            # Safe file path containment check
                            safe_name = Path(uploaded_file.name).name
                            g_dir = (Path(PROJECT_ROOT) / "data" / "geojson").resolve()
                            g_dir.mkdir(parents=True, exist_ok=True)
                            target_file = (g_dir / safe_name).resolve()
                            
                            if not target_file.is_relative_to(g_dir):
                                st.error("Invalid filename path.")
                                os.unlink(tmp_path)
                                return selected_page
                                
                            target_file.write_bytes(uploaded_file.getvalue())

                            features = map_features_to_notes(gdf, source_file=safe_name)
                            all_c = []
                            for feat in features:
                                entities = extract_concepts(feat.get("summary", ""), source_context=safe_name)
                                loc_c = []
                                for e in entities:
                                    name = e.get("name") if isinstance(e, dict) else str(e)
                                    if name:
                                        if name not in all_c: all_c.append(name)
                                        if name not in loc_c: loc_c.append(name)
                                        e_type = e.get("type", "concept") if isinstance(e, dict) else "concept"
                                        cnote = generate_note({"title": name, "summary": e.get("description", "")}, e_type)
                                        write_note(cnote, e_type, name, VAULT_ROOT)
                                feat["linked_concepts"] = loc_c
                                write_note(generate_note(feat, "location"), "location", feat.get("title", "location"), VAULT_ROOT)
                            ds_note = generate_note({
                                "title": safe_name,
                                "source_file": safe_name,
                                "source_format": "geojson",
                                "linked_concepts": all_c,
                                "summary": f"Dataset ingested from {safe_name}"
                            }, "dataset")
                            write_note(ds_note, "dataset", safe_name, VAULT_ROOT)
                                
                        os.unlink(tmp_path)
                        st.success(f"Successfully ingested {uploaded_file.name}!")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Ingestion error: {err}")
            
    return selected_page
