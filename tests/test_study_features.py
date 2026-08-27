"""
Unit tests for Study Graph features (transcription fallback, YouTube downloader, quiz generator, insight extractor).
"""
import pytest
from pathlib import Path

from src.ingestion.audio.transcriber import transcribe_audio
from src.ingestion.youtube.youtube_downloader import download_youtube_audio
from src.quiz.quiz_generator import generate_quiz
from src.quiz.insight_extractor import extract_study_insights

def test_transcribe_audio_offline_fallback(tmp_path):
    # Create dummy audio file
    dummy_audio = tmp_path / "test_lecture.mp3"
    dummy_audio.write_bytes(b"dummy audio data content")

    res = transcribe_audio(dummy_audio)
    assert isinstance(res, dict)
    assert res["filename"] == "test_lecture.mp3"
    assert "sections" in res
    assert len(res["sections"]) > 0
    assert "heading" in res["sections"][0]
    assert "content" in res["sections"][0]

def test_download_youtube_audio_structure():
    # Test downloader with fallback / metadata options
    res = download_youtube_audio("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert isinstance(res, dict)
    assert "title" in res
    assert "url" in res

def test_generate_quiz_fallback(tmp_path):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True)
    concepts_dir = vault_dir / "concepts"
    concepts_dir.mkdir()

    # Create dummy concept note
    note_path = concepts_dir / "Gradient Descent.md"
    note_path.write_text("""---
title: Gradient Descent
type: Concept
---

# Gradient Descent

## Summary
Gradient descent is an iterative optimization algorithm for finding a local minimum of a differentiable function.

## Key Data / Findings
| Parameter | Value |
|---|---|
| Learning Rate | 0.01 |
""", encoding="utf-8")

    quiz = generate_quiz(vault_dir, force_new=False, seed=42)
    assert isinstance(quiz, list)
    assert len(quiz) > 0
    assert "question" in quiz[0]
    assert "type" in quiz[0]

def test_extract_study_insights_fallback(tmp_path):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True)

    insights = extract_study_insights(vault_dir)
    assert isinstance(insights, dict)
    assert "executive_summary" in insights
    assert "hidden_insights" in insights
    assert "exam_alerts" in insights
    assert "cheat_sheet" in insights
