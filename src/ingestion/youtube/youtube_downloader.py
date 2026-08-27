"""
YouTube Video & Playlist Audio Ingestion Module using yt-dlp.
Downloads YouTube audio tracks or auto-generated subtitles for Knowledge Graph processing.
"""
import os
import sys
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def download_youtube_audio(youtube_url: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Download audio and metadata from a YouTube video URL using yt-dlp.
    
    Args:
        youtube_url: Full YouTube video URL or shortened link.
        output_dir: Optional directory to save audio file. Defaults to temp folder.
        
    Returns:
        Dict containing 'title', 'audio_path', 'channel', 'duration', and optional 'subtitle_text'.
    """
    try:
        import yt_dlp
    except ImportError:
        logger.warning("yt-dlp package not installed. Returning fallback YouTube metadata.")
        return {
            "title": f"YouTube Lecture ({youtube_url[:30]})",
            "video_id": "yt_fallback",
            "channel": "YouTube",
            "duration": 0,
            "audio_path": None,
            "subtitle_text": "",
            "url": youtube_url,
            "error": "yt-dlp not installed"
        }

    if output_dir is None:
        output_dir = Path(tempfile.gettempdir()) / "lecture_youtube_downloads"
    output_dir.mkdir(parents=True, exist_ok=True)

    out_template = str(output_dir / "%(id)s.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_template,
        'quiet': True,
        'no_warnings': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Extracting info for YouTube URL: {youtube_url}")
            info = ydl.extract_info(youtube_url, download=True)

            video_id = info.get('id', 'video')
            title = info.get('title', 'YouTube Lecture')
            channel = info.get('uploader') or info.get('channel', 'YouTube Channel')
            duration = info.get('duration', 0)
            
            # Locate downloaded mp3 file
            audio_path = output_dir / f"{video_id}.mp3"
            if not audio_path.exists():
                # Fallback to checking any created audio file for video_id
                possible_files = list(output_dir.glob(f"{video_id}.*"))
                if possible_files:
                    audio_path = possible_files[0]
                else:
                    audio_path = None

            subtitle_text = ""
            # Try parsing VTT subtitle file if downloaded
            sub_files = list(output_dir.glob(f"{video_id}*.vtt")) + list(output_dir.glob(f"{video_id}*.srt"))
            if sub_files:
                try:
                    raw_sub = sub_files[0].read_text(encoding='utf-8')
                    # Strip WebVTT timestamp headers and duplicate lines
                    lines = []
                    for line in raw_sub.splitlines():
                        if "-->" in line or line.startswith("WEBVTT") or line.isdigit() or not line.strip():
                            continue
                        if not lines or lines[-1] != line.strip():
                            lines.append(line.strip())
                    subtitle_text = " ".join(lines)
                except Exception as e:
                    logger.warning(f"Could not parse subtitles: {e}")

            return {
                "title": title,
                "video_id": video_id,
                "channel": channel,
                "duration": duration,
                "audio_path": str(audio_path) if audio_path else None,
                "subtitle_text": subtitle_text,
                "url": youtube_url
            }

    except Exception as e:
        logger.error(f"Error downloading YouTube URL {youtube_url}: {e}")
        # Provide a fallback metadata dict if download fails
        return {
            "title": f"YouTube Lecture ({youtube_url[:30]})",
            "video_id": "yt_fallback",
            "channel": "YouTube",
            "duration": 0,
            "audio_path": None,
            "subtitle_text": "",
            "url": youtube_url,
            "error": str(e)
        }
