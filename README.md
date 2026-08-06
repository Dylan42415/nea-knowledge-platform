# NEA Knowledge Management Platform 🌏

An enterprise-grade Knowledge Management & RAG Platform designed for the National Environment Agency (NEA). Parses PDFs (prose, tables, charts) and GeoJSON datasets into an **Obsidian Vault** knowledge graph, featuring high-precision BM25 retrieval, grounded RAG chatbot, interactive GeoJSON mapping, and Knowledge Graph visualization.

---

## 🚀 Quick Start Guide for Lecturers / Evaluators

### Step 1: Clone or Unzip Project & Setup Virtual Environment
```bash
# Navigate to project directory
cd app

# Create virtual environment
python -m venv .venv

# Activate virtual environment
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
*(Optional: Add your `GEMINI_API_KEY` in `.env`. If no API key is provided, the platform automatically switches to its built-in high-precision deterministic retrieval engine).*

### Step 4: Run the Streamlit Application
```bash
streamlit run src/app/streamlit_app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 📊 Features & Navigation Pages

1. **📊 Dashboard**: Metrics overview of ingested documents, concepts, locations, and organizations.
2. **📖 Browse Notes**: Search and browse Gold Standard Obsidian wiki notes with metadata badges and tags.
3. **🗺️ Map View**: Interactive PyDeck map rendering spatial GeoJSON data layers over Singapore.
4. **🕸️ Knowledge Graph**: Interactive force-directed network graph visualizing `[[Wikilinks]]` across vault concepts.
5. **💬 Chat with Vault**: High-precision RAG chatbot with BM25 term frequency saturation, title boosting, and grounded source citations (`soe_report.pdf, pp. 14-15`).

---

## 🧪 Running Automated Tests
```bash
pytest tests/ -v
```

---

## 📂 Project Structure

```
app/
├── ObsidianVault/
│   └── vault/              # Populated Obsidian Knowledge Vault
│       ├── concepts/       # Gold Standard concept wiki notes
│       ├── datasets/       # Dataset metadata notes
│       ├── locations/      # Spatial location notes
│       └── organizations/  # Agency and organization notes
├── src/
│   ├── app/                # Multi-page Streamlit portal
│   ├── chat/               # BM25 Retrieval Engine & RAG Chatbot
│   ├── extraction/         # Gold Standard Topic Extractor & Prompts
│   ├── ingestion/          # PDF (PyMuPDF / Docling) & GeoJSON parsers
│   └── vault_writer/       # Note generator & link resolver
├── scripts/                # Ingestion & CLI utilities
├── tests/                  # Pytest unit test suite
├── requirements.txt        # Package dependencies
├── .env.example            # Environment configuration template
└── README.md               # Quick start documentation
```
