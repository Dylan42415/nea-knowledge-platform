"""
Lecture Audio Recorder & Ingestion View Page.
Allows live audio recording, audio file upload, or YouTube link ingestion.
"""
import os
import tempfile
from pathlib import Path
import streamlit as st

from src.config import VAULT_ROOT
from src.ingestion.audio.transcriber import transcribe_audio
from src.ingestion.youtube.youtube_downloader import download_youtube_audio
from src.extraction.gold_extractor import extract_gold_notes
from src.vault_writer.note_generator import generate_note, write_note
from src.vault_writer.linker import finalize_vault_wikilinks

def render_lecture_recorder_view():
    st.header("🎙️ Record & Ingest Lecture")
    st.caption("Convert live lecture audio, recordings, or YouTube videos directly into your Obsidian Knowledge Graph.")

    tab1, tab2, tab3 = st.tabs(["▶️ YouTube Link Ingestion", "🎙️ Live Audio Recording", "📁 File Upload"])

    # --- TAB 1: YOUTUBE INGESTION ---
    with tab1:
        st.subheader("Ingest YouTube Lecture")
        st.markdown("Paste any YouTube URL (lecture recording, tutorial, or university talk). We will download the audio track / subtitles and build your knowledge graph.")
        
        yt_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...", key="recorder_yt_url")
        
        if yt_url and st.button("🚀 Process YouTube Lecture", type="primary", key="btn_yt_process"):
            with st.spinner("Downloading YouTube video metadata & audio with yt-dlp..."):
                try:
                    yt_data = download_youtube_audio(yt_url)
                    title = yt_data.get("title", "YouTube Lecture")
                    channel = yt_data.get("channel", "YouTube")
                    duration = yt_data.get("duration", 0)
                    audio_path = yt_data.get("audio_path")
                    subtitles = yt_data.get("subtitle_text")

                    st.info(f"📹 **Found Video**: {title} | **Channel**: {channel} | **Duration**: {duration//60}m {duration%60}s")

                    with st.spinner("Transcribing audio into structured sections..."):
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
                    st.success(f"Extracted {len(sections)} timestamped sections!")

                    with st.spinner("Extracting academic concepts & generating Gold Vault Notes..."):
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

                    st.balloons()
                    st.success(f"🎉 YouTube Lecture **[[{title}]]** successfully converted into Knowledge Graph! Check the Knowledge Graph page.")
                    
                except Exception as e:
                    st.error(f"Error processing YouTube URL: {e}")

    # --- TAB 2: LIVE AUDIO RECORDING ---
    with tab2:
        st.subheader("Live Audio Recorder")
        st.markdown("Record audio directly from your microphone during class or a study session.")

        audio_value = st.audio_input("Record lecture audio")
        lecture_title_rec = st.text_input("Lecture Title", value="Live Lecture Session", key="rec_title")

        if audio_value is not None:
            st.audio(audio_value)
            if st.button("Process Live Recording", type="primary", key="btn_rec_process"):
                with st.spinner("Transcribing live recording with Gemini Audio..."):
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                            tmp.write(audio_value.getvalue())
                            tmp_path = Path(tmp.name)

                        t_data = transcribe_audio(tmp_path)
                        sections = t_data.get("sections", [])

                        extracted_concepts = []
                        for sec in sections:
                            payload = {
                                "title": sec.get("heading", lecture_title_rec),
                                "content": sec.get("content", ""),
                                "source_document": lecture_title_rec,
                                "source_location": f"Timestamp {sec.get('timestamp', '00:00')}"
                            }
                            gold_notes = extract_gold_notes(payload)
                            for n in gold_notes:
                                name = n.get("title", "Concept")
                                if name not in extracted_concepts: extracted_concepts.append(name)
                                cnote = generate_note(n, n.get("type", "Concept"))
                                write_note(cnote, n.get("type", "Concept"), name, VAULT_ROOT)

                        ds_note = generate_note({
                            "title": lecture_title_rec,
                            "source_file": lecture_title_rec,
                            "source_format": "audio_recording",
                            "linked_concepts": extracted_concepts,
                            "summary": f"Live lecture recording ingested on topic {lecture_title_rec}"
                        }, "dataset")
                        write_note(ds_note, "dataset", lecture_title_rec, VAULT_ROOT)
                        finalize_vault_wikilinks(VAULT_ROOT)
                        os.unlink(tmp_path)

                        st.balloons()
                        st.success(f"🎉 Recording **[[{lecture_title_rec}]]** ingested!")
                    except Exception as e:
                        st.error(f"Error processing recording: {e}")

    # --- TAB 3: FILE UPLOAD ---
    with tab3:
        st.subheader("Upload Audio or PDF Slides")
        st.markdown("Upload existing lecture audio files (`.mp3`, `.wav`, `.m4a`, `.ogg`) or slide deck PDFs.")

        up_file = st.file_uploader("Choose file", type=["mp3", "wav", "m4a", "ogg", "webm", "pdf"], key="rec_uploader")
        if up_file is not None:
            if st.button("Process File Ingestion", type="primary", key="btn_file_process"):
                with st.spinner(f"Ingesting {up_file.name}..."):
                    try:
                        ext = Path(up_file.name).suffix.lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                            tmp.write(up_file.getvalue())
                            tmp_path = Path(tmp.name)

                        if ext in [".mp3", ".wav", ".m4a", ".ogg", ".webm"]:
                            t_data = transcribe_audio(tmp_path)
                            sections = t_data.get("sections", [])
                            extracted_concepts = []
                            for sec in sections:
                                payload = {
                                    "title": sec.get("heading", up_file.name),
                                    "content": sec.get("content", ""),
                                    "source_document": up_file.name,
                                    "source_location": f"Timestamp {sec.get('timestamp', '00:00')}"
                                }
                                gold_notes = extract_gold_notes(payload)
                                for n in gold_notes:
                                    name = n.get("title", "Concept")
                                    if name not in extracted_concepts: extracted_concepts.append(name)
                                    cnote = generate_note(n, n.get("type", "Concept"))
                                    write_note(cnote, n.get("type", "Concept"), name, VAULT_ROOT)

                            ds_note = generate_note({
                                "title": up_file.name,
                                "source_file": up_file.name,
                                "source_format": "audio",
                                "linked_concepts": extracted_concepts,
                                "summary": f"Lecture audio recording ingested from {up_file.name}"
                            }, "dataset")
                            write_note(ds_note, "dataset", up_file.name, VAULT_ROOT)

                        elif ext == ".pdf":
                            from src.ingestion.pdf.classifier import classify_pdf
                            from src.ingestion.pdf.pymupdf_parser import extract_text
                            from src.ingestion.pdf.docling_parser import extract_with_layout
                            from src.extraction.topic_aggregator import aggregate_topics_from_document

                            pdf_type = classify_pdf(tmp_path)
                            parsed = extract_text(tmp_path) if pdf_type == "text" else extract_with_layout(tmp_path)
                            topic_payloads = aggregate_topics_from_document(parsed, doc_filename=up_file.name)
                            extracted_concepts = []
                            for payload in topic_payloads:
                                gold_notes = extract_gold_notes(payload)
                                for n in gold_notes:
                                    name = n.get("title", "Concept")
                                    if name not in extracted_concepts: extracted_concepts.append(name)
                                    cnote = generate_note(n, n.get("type", "Concept"))
                                    write_note(cnote, n.get("type", "Concept"), name, VAULT_ROOT)

                            ds_note = generate_note({
                                "title": up_file.name,
                                "source_file": up_file.name,
                                "source_format": "pdf",
                                "linked_concepts": extracted_concepts,
                                "summary": f"Lecture slide PDF ingested from {up_file.name}"
                            }, "dataset")
                            write_note(ds_note, "dataset", up_file.name, VAULT_ROOT)

                        finalize_vault_wikilinks(VAULT_ROOT)
                        os.unlink(tmp_path)
                        st.balloons()
                        st.success(f"Successfully processed {up_file.name}!")
                    except Exception as err:
                        st.error(f"Ingestion error: {err}")
