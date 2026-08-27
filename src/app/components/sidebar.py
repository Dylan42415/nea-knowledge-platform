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
from src.ingestion.audio.transcriber import transcribe_audio
from src.ingestion.youtube.youtube_downloader import download_youtube_audio
from src.extraction.gold_extractor import extract_gold_notes
from src.vault_writer.note_generator import generate_note, write_note
from src.vault_writer.linker import finalize_vault_wikilinks
from src.workspace.workspace_manager import (
    get_workspace_data,
    get_all_lecture_files,
    is_valid_scope_selected
)

@st.cache_data(ttl=30)
def get_vault_stats(vault_root_str: str):
    """Cached vault note file counters."""
    vault_dir = Path(vault_root_str)
    doc_count = len(list((vault_dir / "datasets").rglob("*.md"))) if (vault_dir / "datasets").exists() else 0
    concept_count = len(list((vault_dir / "concepts").rglob("*.md"))) if (vault_dir / "concepts").exists() else 0
    location_count = len(list((vault_dir / "locations").rglob("*.md"))) if (vault_dir / "locations").exists() else 0
    org_count = len(list((vault_dir / "organizations").rglob("*.md"))) if (vault_dir / "organizations").exists() else 0
    return doc_count, concept_count, location_count, org_count

def render_sidebar() -> str:
    """
    Renders the sidebar with active scope selector, navigation, stats, and audio/YouTube ingestion.
    Hides the 4 tool pages until a valid Subject or File is selected.
    """
    doc_count, concept_count, location_count, org_count = get_vault_stats(str(VAULT_ROOT))
    total_notes = doc_count + concept_count + location_count + org_count
    vault_dir = Path(VAULT_ROOT)

    with st.sidebar:
        st.title("🎓 StudyGraph AI")
        st.caption("Lecture Audio & YouTube Knowledge Graph Platform")
        
        st.markdown("---")

        # --- ACTIVE STUDY SCOPE SELECTOR ---
        st.subheader("🎯 Step 1: Select Subject or File")
        ws_data = get_workspace_data(vault_dir)
        subjects = list(ws_data.get("subjects", {}).keys())
        all_files = get_all_lecture_files(vault_dir)

        scope_options = ["-- Select a Subject or File --"]
        for s in subjects:
            scope_options.append(f"Subject: {s}")
        for f in all_files:
            scope_options.append(f"File: {f}")
        scope_options.append("🌐 All Files (Global Vault)")

        current_scope_idx = 0
        if "active_study_scope" in st.session_state and st.session_state["active_study_scope"] in scope_options:
            current_scope_idx = scope_options.index(st.session_state["active_study_scope"])

        selected_scope = st.selectbox(
            "Target Study Scope:",
            scope_options,
            index=current_scope_idx,
            key="sb_scope_selector"
        )
        st.session_state["active_study_scope"] = selected_scope

        scope_is_valid = is_valid_scope_selected(selected_scope)

        st.markdown("---")
        st.subheader("Step 2: Navigation & Tools")

        # Only reveal tool pages WHEN scope_is_valid is True!
        if scope_is_valid:
            nav_options = [
                '📁 Subject Workspaces',
                '🎙️ Ingest Lecture / YouTube',
                '🕸️ Knowledge Graph & Chat',
                '💡 Study Guide & Insights',
                '📝 Active Recall Quiz',
                '📖 Browse Study Notes'
            ]
        else:
            nav_options = [
                '📁 Subject Workspaces',
                '🎙️ Ingest Lecture / YouTube'
            ]
            st.info("💡 Select a Subject or File above to reveal Knowledge Graph, Study Guide, Quiz, and Notes.")

        nav_index = 0
        if "navigation_target" in st.session_state:
            target = st.session_state["navigation_target"]
            if target in nav_options:
                nav_index = nav_options.index(target)
            del st.session_state["navigation_target"]

        selected_page = st.radio(
            "Go to",
            nav_options,
            index=nav_index,
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.subheader("Vault Metrics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Total Notes", value=str(total_notes))
            st.metric(label="Concepts", value=str(concept_count))
        with col2:
            st.metric(label="Lectures", value=str(doc_count))
            st.metric(label="Orgs/Links", value=str(org_count))
            
        st.markdown("---")
        st.subheader("⚡ Quick Ingest Audio / YouTube")
        
        # YouTube URL Input
        yt_url = st.text_input("YouTube Lecture URL", placeholder="https://www.youtube.com/watch?v=...")
        if yt_url and st.button("Process YouTube Video", type="primary", use_container_width=True):
            with st.spinner("Downloading YouTube video & generating Knowledge Graph..."):
                try:
                    yt_data = download_youtube_audio(yt_url)
                    audio_path = yt_data.get("audio_path")
                    title = yt_data.get("title", "YouTube Lecture")
                    subtitles = yt_data.get("subtitle_text")

                    if audio_path and Path(audio_path).exists():
                        t_data = transcribe_audio(audio_path)
                    elif subtitles:
                        t_data = {
                            "filename": title,
                            "sections": [{"heading": title, "timestamp": "00:00", "content": subtitles}]
                        }
                    else:
                        t_data = transcribe_audio(Path("sample.mp3"))

                    sections = t_data.get("sections", [])
                    extracted_concepts = []
                    for sec in sections:
                        payload = {
                            "title": sec.get("heading", title),
                            "content": sec.get("content", ""),
                            "source_document": f"YouTube: {title}",
                            "source_location": f"Timestamp {sec.get('timestamp', '00:00')}"
                        }
                        gold_notes = extract_gold_notes(payload)
                        for n in gold_notes:
                            name = n.get("title", "Concept")
                            if name not in extracted_concepts: extracted_concepts.append(name)
                            cnote = generate_note(n, n.get("type", "Concept"))
                            write_note(cnote, n.get("type", "Concept"), name, VAULT_ROOT)

                    ds_note = generate_note({
                        "title": title,
                        "source_file": yt_url,
                        "source_format": "youtube",
                        "linked_concepts": extracted_concepts,
                        "summary": f"YouTube lecture recording ingested from {yt_url}"
                    }, "dataset")
                    write_note(ds_note, "dataset", title, VAULT_ROOT)
                    finalize_vault_wikilinks(VAULT_ROOT)

                    # Auto-set active scope to newly ingested video
                    st.session_state["active_study_scope"] = f"File: {title}"
                    st.success(f"Successfully processed YouTube video: {title}!")
                    st.rerun()
                except Exception as err:
                    st.error(f"YouTube ingestion error: {err}")

        # Audio / Document File Uploader
        uploaded_file = st.file_uploader("Upload Audio or PDF File", type=["mp3", "wav", "m4a", "ogg", "webm", "pdf"])
        if uploaded_file is not None:
            if st.button("Process Uploaded File", use_container_width=True):
                with st.spinner(f"Ingesting {uploaded_file.name}..."):
                    try:
                        ext = Path(uploaded_file.name).suffix.lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = Path(tmp.name)

                        if ext in [".mp3", ".wav", ".m4a", ".ogg", ".webm"]:
                            t_data = transcribe_audio(tmp_path)
                            sections = t_data.get("sections", [])
                            extracted_concepts = []
                            for sec in sections:
                                payload = {
                                    "title": sec.get("heading", uploaded_file.name),
                                    "content": sec.get("content", ""),
                                    "source_document": uploaded_file.name,
                                    "source_location": f"Timestamp {sec.get('timestamp', '00:00')}"
                                }
                                gold_notes = extract_gold_notes(payload)
                                for n in gold_notes:
                                    name = n.get("title", "Concept")
                                    if name not in extracted_concepts: extracted_concepts.append(name)
                                    cnote = generate_note(n, n.get("type", "Concept"))
                                    write_note(cnote, n.get("type", "Concept"), name, VAULT_ROOT)

                            ds_note = generate_note({
                                "title": uploaded_file.name,
                                "source_file": uploaded_file.name,
                                "source_format": "audio",
                                "linked_concepts": extracted_concepts,
                                "summary": f"Lecture audio recording ingested from {uploaded_file.name}"
                            }, "dataset")
                            write_note(ds_note, "dataset", uploaded_file.name, VAULT_ROOT)

                        elif ext == ".pdf":
                            from src.ingestion.pdf.classifier import classify_pdf
                            from src.ingestion.pdf.pymupdf_parser import extract_text
                            from src.ingestion.pdf.docling_parser import extract_with_layout
                            from src.extraction.topic_aggregator import aggregate_topics_from_document

                            pdf_type = classify_pdf(tmp_path)
                            parsed = extract_text(tmp_path) if pdf_type == "text" else extract_with_layout(tmp_path)
                            topic_payloads = aggregate_topics_from_document(parsed, doc_filename=uploaded_file.name)
                            extracted_concepts = []
                            for payload in topic_payloads:
                                gold_notes = extract_gold_notes(payload)
                                for n in gold_notes:
                                    name = n.get("title", "Concept")
                                    if name not in extracted_concepts: extracted_concepts.append(name)
                                    cnote = generate_note(n, n.get("type", "Concept"))
                                    write_note(cnote, n.get("type", "Concept"), name, VAULT_ROOT)

                            ds_note = generate_note({
                                "title": uploaded_file.name,
                                "source_file": uploaded_file.name,
                                "source_format": "pdf",
                                "linked_concepts": extracted_concepts,
                                "summary": f"Lecture slide PDF ingested from {uploaded_file.name}"
                            }, "dataset")
                            write_note(ds_note, "dataset", uploaded_file.name, VAULT_ROOT)

                        finalize_vault_wikilinks(VAULT_ROOT)
                        os.unlink(tmp_path)

                        # Auto-set active scope
                        st.session_state["active_study_scope"] = f"File: {uploaded_file.name}"
                        st.success(f"Successfully processed {uploaded_file.name}!")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Ingestion error: {err}")

    return selected_page
