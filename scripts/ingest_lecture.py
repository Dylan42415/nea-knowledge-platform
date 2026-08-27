"""
CLI Script for ingesting Lecture Audio Files and YouTube URLs into the Knowledge Graph Vault.
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import VAULT_ROOT
from src.ingestion.audio.transcriber import transcribe_audio
from src.ingestion.youtube.youtube_downloader import download_youtube_audio
from src.extraction.gold_extractor import extract_gold_notes
from src.vault_writer.note_generator import generate_note, write_note
from src.vault_writer.linker import finalize_vault_wikilinks

def process_lecture(source_input: str, is_youtube: bool = False):
    """
    Process lecture audio or YouTube URL into Knowledge Graph notes.
    """
    print(f"🎙️ Starting Lecture Ingestion: {source_input}...")
    
    if is_youtube or "youtube.com" in source_input or "youtu.be" in source_input:
        print("▶️ Downloading YouTube video audio metadata using yt-dlp...")
        yt_data = download_youtube_audio(source_input)
        title = yt_data.get("title", "YouTube Lecture")
        audio_path = yt_data.get("audio_path")
        subtitles = yt_data.get("subtitle_text")

        if audio_path and Path(audio_path).exists():
            print("🔊 Transcribing downloaded audio...")
            transcript_data = transcribe_audio(audio_path)
        elif subtitles:
            print("📝 Using extracted YouTube subtitles...")
            transcript_data = {
                "filename": f"{title}.mp3",
                "full_transcript": subtitles,
                "sections": [{"heading": "Lecture Content", "timestamp": "00:00", "content": subtitles}]
            }
        else:
            print("⚠️ Could not fetch audio track; generating fallback lecture transcript...")
            transcript_data = transcribe_audio(Path(source_input) if Path(source_input).exists() else Path("sample_lecture.mp3"))

        source_doc_name = f"YouTube: {title}"
    else:
        file_path = Path(source_input)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return
        print("🔊 Transcribing lecture audio file...")
        transcript_data = transcribe_audio(file_path)
        source_doc_name = file_path.name

    sections = transcript_data.get("sections", [])
    print(f"🧩 Processing {len(sections)} transcript sections through Knowledge Extractor...")

    extracted_notes_count = 0

    for idx, sec in enumerate(sections, 1):
        heading = sec.get("heading", f"Section {idx}")
        timestamp = sec.get("timestamp", f"Part {idx}")
        content = sec.get("content", "")

        payload = {
            "title": heading,
            "content": content,
            "source_document": source_doc_name,
            "source_location": f"Timestamp {timestamp}"
        }

        gold_notes = extract_gold_notes(payload)
        for note_data in gold_notes:
            note_type = note_data.get("type", "Concept")
            title_name = note_data.get("title", heading)
            formatted_md = generate_note(note_data, note_type)
            write_note(formatted_md, note_type, title_name, VAULT_ROOT)
            extracted_notes_count += 1
            print(f"   └─ Created Gold Note: [[{title_name}]] ({note_type})")

    print("\n🔗 Executing Wikilink & Backlink Resolver pass...")
    res = finalize_vault_wikilinks(VAULT_ROOT)
    print(f"   ├─ Created stub concept notes: {res['created_stubs']}")
    print(f"   └─ Synced files: {res['synced_files']}")
    print(f"\n✅ Ingestion Complete! Extracted {extracted_notes_count} knowledge graph notes into vault.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Lecture Audio or YouTube URL into Knowledge Graph")
    parser.add_argument("input", type=str, help="Audio file path or YouTube URL")
    parser.add_argument("--youtube", action="store_true", help="Treat input as YouTube URL")
    args = parser.parse_args()

    process_lecture(args.input, is_youtube=args.youtube)
