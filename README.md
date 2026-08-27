# StudyGraph AI 🎓 — Lecture Audio & YouTube Knowledge Graph Platform

An enterprise-grade AI studying platform that converts live lecture recordings, audio files, YouTube videos (`yt-dlp`), and slide PDFs into an interactive **Obsidian Knowledge Graph**. Features node-level AI chatbot Q&A, automatic wikilink node resolution (`[[Wikilinks]]`), active recall quizzes, hidden lecture insights, and formula cheat sheets.

---

## 🚀 Quick Start Guide

### Step 1: Virtual Environment Setup
```bash
# Navigate to project directory
cd audioapp

# Create & activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment (.env)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optional: Add your `GEMINI_API_KEY` in `.env`. If no API key is provided, the platform automatically runs using built-in high-precision offline transcription and fallback retrieval engines).*

### Step 4: Run the Streamlit Application
```bash
streamlit run src/app/streamlit_app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 📊 Features & Navigation Pages

1. **🎙️ Record / Ingest Lecture**: Live audio recording in browser, audio file upload (`.mp3`, `.wav`, `.m4a`), or **YouTube Video URL Ingestion** (`yt-dlp`).
2. **🕸️ Knowledge Graph & Chat**: Interactive force-directed network graph visualizing `[[Wikilinks]]`. Click any node or select a concept to inspect note details and ask the **In-Graph AI Chatbot** targeted questions.
3. **💡 Study Guide & Insights**: Audio executive summaries, hidden conceptual insights, exam alerts, and formula cheat sheets.
4. **📝 Active Recall Quiz**: Interactive Multiple Choice questions and Flashcards with instant answer explanations, **"Redo Current Quiz"**, and **"Regenerate New Questions"** features.
5. **📖 Browse Study Notes**: Search and browse Gold Standard Obsidian wiki notes with metadata badges and tags.

---

## 💻 CLI Command Ingestion (Audio / YouTube)

```bash
# Ingest a YouTube lecture URL
python scripts/ingest_lecture.py "https://www.youtube.com/watch?v=YOUR_VIDEO_ID" --youtube

# Ingest a local audio recording file
python scripts/ingest_lecture.py "path/to/lecture_recording.mp3"
```

---

## 🧪 Running Automated Tests
```bash
.venv\Scripts\python -m pytest tests/ -v
```

---

## 📂 Project Structure

```
audioapp/
├── ObsidianVault/
│   └── vault/              # Populated Obsidian Knowledge Vault
│       ├── concepts/       # Academic concept wiki notes
│       ├── datasets/       # Lecture transcript & source notes
│       ├── locations/      # Spatial/facility notes
│       └── organizations/  # Standards and organizations
├── src/
│   ├── app/                # Multi-page Streamlit portal
│   │   ├── components/     # Sidebar & UI components
│   │   └── views/          # Lecture recorder, Graph View, Study Guide, Quiz, Browse
│   ├── chat/               # BM25 Retrieval Engine & RAG Chatbot
│   ├── extraction/         # Academic Gold Standard Extractor & Prompts
│   ├── ingestion/          # Audio (Gemini), YouTube (yt-dlp), & PDF parsers
│   ├── quiz/               # Quiz generator & Study Insight extractor
│   └── vault_writer/       # Note generator & link resolver
├── scripts/                # Ingestion & CLI utilities (ingest_lecture.py)
├── tests/                  # Pytest unit test suite (17 unit tests)
├── requirements.txt        # Package dependencies (includes yt-dlp)
├── .env.example            # Environment configuration template
└── README.md               # Quick start documentation
```
