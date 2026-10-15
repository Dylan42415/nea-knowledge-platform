# 🌏 National Environment Agency (NEA) Knowledge Platform — System Architecture & Codebase Breakdown

## 📌 Executive Overview

The **NEA Knowledge Platform** is an enterprise-grade Knowledge Management and RAG Systems Platform designed for ingesting, structuring, linking, and analyzing environmental datasets (PDF reports, GeoJSON spatial layers, statutory benchmarks). 

It converts raw unstructured documentation into a 100% grounded **Obsidian Knowledge Graph** with structured YAML frontmatter, typed wikilinks (`[[Wikilinks]]`), and mathematical BM25 relevance ranking for zero-hallucination AI chat assistance.

---

## 🏗️ High-Level System Architecture

```mermaid
flowchart TD
    subgraph Data Sources
        PDF[PDF Reports e.g. soe_report.pdf]
        GeoJSON[GeoJSON Datasets e.g. Marina Bay]
    end

    subgraph Ingestion & Chunking
        Classifier[PDF Classifier text vs scanned]
        PyMuPDF[PyMuPDF Parser]
        Docling[Docling Layout Parser]
        GeoLoader[GeoPandas Loader & CRS Validator]
        Chunker[Structure-Aware Chunker]
    end

    subgraph Extraction & Aggregation
        TopicAgg[4-Page Sliding Topic Window Aggregator]
        GoldExtract[Gemini Gold Extractor + Heuristic Fallback]
        DensityEngine[Data Density Scoring Engine]
    end

    subgraph Obsidian Knowledge Vault
        Datasets[vault/datasets/]
        Concepts[vault/concepts/]
        Locations[vault/locations/]
        Organizations[vault/organizations/]
    end

    subgraph Chat Engine & Retrieval
        BM25[Length-Normalized BM25 Ranker]
        IntentRouter[Intent Router & Ontology Auditor]
        SubQuery[Multi-Domain Sub-Query Decomposer]
        Gemini[Gemini Flash RAG LLM]
    end

    subgraph Frontend Application
        Dashboard[Dashboard & Metrics]
        Browse[Vault Note Browser]
        MapView[Pydeck Map View]
        GraphView[Streamlit-AGraph Knowledge Graph]
        ChatView[Chat with Vault Assistant]
    end

    PDF --> Classifier
    Classifier -->|Native Text| PyMuPDF
    Classifier -->|Scanned / Complex| Docling
    PyMuPDF --> Chunker
    Docling --> Chunker
    Chunker --> TopicAgg
    TopicAgg --> GoldExtract

    GeoJSON --> GeoLoader
    GeoLoader --> Mapper[GeoJSON Feature Mapper]
    Mapper --> GoldExtract

    GoldExtract --> DensityEngine
    DensityEngine --> Datasets
    DensityEngine --> Concepts
    DensityEngine --> Locations
    DensityEngine --> Organizations

    Obsidian Vault --> BM25
    BM25 --> SubQuery
    SubQuery --> IntentRouter
    IntentRouter --> Gemini

    Gemini --> ChatView
    Obsidian Vault --> Dashboard
    Obsidian Vault --> Browse
    Obsidian Vault --> MapView
    Obsidian Vault --> GraphView
```

---

## 📂 Directory & File Structure

```
c:\Users\Dfault\Downloads\app\
├── .venv/                      # Python 3.10 virtual environment
├── ObsidianVault/
│   └── vault/                  # Local Obsidian Markdown Vault
│       ├── datasets/           # Ingested dataset source notes
│       ├── concepts/           # Scientific metrics, parameters & pollutants
│       ├── locations/          # Spatial features with lat/lon centroids
│       └── organizations/      # Statutory agencies (NEA, PUB, MSS, MOH)
├── scripts/
│   ├── ingest_pdf.py           # CLI runner for PDF ingestion
│   ├── ingest_geojson.py       # CLI runner for GeoJSON ingestion
│   ├── fix_ontology_issues.py  # Automated vault ontology normalization script
│   └── reingest_gold_vault.py  # Batch Gold Standard re-ingestion runner
├── src/
│   ├── __init__.py
│   ├── config.py               # Path constants, env variables & vault directories
│   ├── app/                    # Streamlit Multi-Page Web Application
│   │   ├── __init__.py
│   │   ├── streamlit_app.py    # Main entry point, dark theme CSS & routing
│   │   ├── components/
│   │   │   ├── sidebar.py      # Cached vault stats & file uploader
│   │   │   ├── note_card.py    # Glassmorphism HTML note card component
│   │   │   └── search_bar.py   # Vault search bar component
│   │   └── views/
│   │       ├── browse.py       # Browse & search vault notes
│   │       ├── chat_view.py    # Grounded Gemini RAG Chatbot view
│   │       ├── graph_view.py   # Interactive Knowledge Graph view
│   │       └── map_view.py     # Pydeck spatial map view
│   ├── chat/                   # RAG Engine & Vault Search
│   │   ├── __init__.py
│   │   ├── vault_index.py      # BM25 term frequency ranker with title/alias boosting
│   │   └── chat_engine.py      # Gemini RAG chatbot, intent router & offline synthesis
│   ├── db/                     # Supabase & PostgreSQL Client
│   │   ├── client.py           # Supabase client wrapper & psycopg2 connection
│   │   └── models.py           # SQL DDL table schemas (documents, concepts, locations, chunks)
│   ├── extraction/             # Information Extraction
│   │   ├── concept_extractor.py# Regex fallback concept extractor
│   │   ├── gold_extractor.py   # Gemini Gold Extractor with heuristic fallback
│   │   └── topic_aggregator.py # 4-page sliding window document aggregator
│   ├── ingestion/              # Format-Specific Document Processing
│   │   ├── geojson/
│   │   │   ├── feature_mapper.py# GeoJSON feature to note mapper
│   │   │   └── loader.py       # GeoPandas loader & CRS validator
│   │   └── pdf/
│   │       ├── chunker.py      # Structure-aware heading chunker
│   │       ├── classifier.py   # PyMuPDF >80% text classifier
│   │       ├── docling_parser.py# Layout-aware Docling parser
│   │       └── pymupdf_parser.py# Fast PyMuPDF text parser
│   └── vault_writer/           # Markdown & Link Management
│       ├── linker.py           # Wikilink resolver & backlink scanner
│       └── note_generator.py   # YAML frontmatter generator & Data Density Scoring engine
└── tests/                      # Pytest Unit Test Suite (13 unit tests)
    ├── test_chat_engine.py
    ├── test_concept_extractor.py
    ├── test_geojson_loader.py
    ├── test_pdf_parser.py
    └── test_vault_writer.py
```

---

## ⚡ Core Pipeline Breakdown

### 1. Document Ingestion Pipeline (`src/ingestion/`)

#### A. PDF Processing
1. **Classification (`classifier.py`)**: PyMuPDF checks if >80% of pages have extractable text. If true, classified as `'text'`; otherwise `'scanned'`.
2. **Parsing (`pymupdf_parser.py` / `docling_parser.py`)**:
   - `pymupdf_parser.py` rapidly extracts text page-by-page.
   - `docling_parser.py` performs layout-aware structure parsing (preserving heading hierarchy and data tables).
3. **Chunking (`chunker.py`)**: Splits text at section heading boundaries rather than fixed token windows, keeping tables and figures as distinct chunks.

#### B. GeoJSON Processing
1. **Loading & Validation (`loader.py`)**: Uses GeoPandas (`gpd.read_file`) to load `.geojson` / `.json` files and validates geometry types and Coordinate Reference Systems (defaulting to `EPSG:4326` WGS84).
2. **Feature Mapping (`feature_mapper.py`)**: Computes centroid coordinates (`lat/lon`) for each spatial feature and maps properties into structured location note attributes.

---

### 2. Information Extraction & Density Scoring (`src/extraction/` & `src/vault_writer/`)

1. **Topical Window Aggregation (`topic_aggregator.py`)**: Bundles 4-page sliding document windows to preserve context across multi-page tables and discussions.
2. **Gold Concept Extraction (`gold_extractor.py`)**:
   - Uses Gemini Flash API to extract named entities (`Pollutant`, `Indicator`, `Concept`, `Facility`, `Organization`, `Policy`).
   - If Gemini returns rate limits (`429`), falls back to `_heuristic_gold_fallback()` which parses markdown tables and filters out pure numeric headers (`if title.isdigit(): return []`).
3. **Data Density Scoring Engine (`note_generator.py`)**:
   Prevents shallow parameter stubs from overwriting rich numerical notes using a weighted score:
   $$\text{Density Score} = (10 \times \text{Table Rows}) + (5 \times \text{Numerical Metrics}) + (2 \times \text{Wikilinks}) + \frac{\text{Length}}{100}$$
   When a note exists on disk, `write_note()` compares scores and merges new findings tables under `### Additional Findings`.

---

### 3. RAG Retrieval & Chat Engine (`src/chat/`)

#### A. BM25 Relevance Ranker (`vault_index.py`)
- **Cached Disk Scanner (`_get_cached_vault_notes`)**: Uses Streamlit `@st.cache_data(ttl=30)` to cache the 53 parsed vault notes in memory.
- **BM25 Term Saturation**:
  $$\text{BM25 Score} = \text{IDF}(t) \times \frac{f(t, D) \cdot (k_1 + 1)}{f(t, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$
  Where $k_1 = 1.2$, $b = 0.75$, with exact entity title boosting ($+100$) and YAML `aliases: [...]` matching.

#### B. Dynamic Retrieval & Intent Routing (`chat_engine.py`)
- **Dynamic `max_notes` Expansion**: Broad queries (*"all"*, *"summary"*, *"overview"*, *"data points"*) automatically scale retrieval from 5 to 12 notes.
- **Sub-Query Decomposition**: Multi-domain queries (*"air and water quality"*) decompose into parallel sub-queries (`air quality pollutants` + `water quality parameters`) to prevent domain crowding.
- **Intent Routing**:
  - `_audit_vault_ontology()`: Evaluates predicate taxonomy (`MANAGED_BY`, `BENCHMARKED_AGAINST`) and naming variations.
  - `_analyze_knowledge_graph_hubs()`: Calculates Top 10 central hubs sorted by degree centrality.
  - `_offline_fallback_response()`: High-precision deterministic multi-note synthesis fallback when Gemini API is offline.

---

### 4. Web Application & Frontend (`src/app/`)

- **Main Entry Point (`streamlit_app.py`)**: Implements custom CSS theme (dark slate `#0b0f17` background, glassmorphism cards, Inter font typography, high-contrast dark inputs).
- **Sidebar (`components/sidebar.py`)**: Caches vault file counters (`doc_count`, `concept_count`, `location_count`, `org_count`) via `@st.cache_data(ttl=30)` for instant navigation.
- **Views**:
  - `browse.py`: Search and filter 53 notes by category and tags with expandable full content.
  - `chat_view.py`: Conversational RAG interface with 1-click suggested prompts, input box, and `Clear Chat 🗑️` session purging.
  - `graph_view.py`: Interactive knowledge graph visualization powered by `streamlit-agraph`.
  - `map_view.py`: Spatial visualization centered on Singapore (`lat=1.3521, lon=103.8198`) using Pydeck.

---

## 🛠️ Technology Stack

| Category | Component / Technology | Purpose |
| :--- | :--- | :--- |
| **Language & Runtime** | Python 3.10 | Core platform execution environment |
| **Web Framework** | Streamlit 1.30+ | Multi-page interactive web application |
| **PDF Ingestion** | PyMuPDF (`fitz`), Docling | Text extraction, layout parsing, and chunking |
| **Spatial Ingestion** | GeoPandas, Shapely | GeoJSON parsing, CRS validation, centroid calculation |
| **AI & LLM** | Google Gemini Flash API | Concept extraction and grounded RAG answer synthesis |
| **Information Retrieval** | Custom BM25 Engine | Saturation scoring, length normalization, title/alias boosting |
| **Database** | Supabase, PostgreSQL (`psycopg2`) | Cloud document metadata and vector storage |
| **Graph Visualization** | `streamlit-agraph` | Interactive node-edge knowledge graph rendering |
| **Map Visualization** | Pydeck | High-performance spatial layer rendering |
| **Testing** | Pytest | Unit test suite verifying core components |

---

## 🧪 Verification & Test Suite

The platform includes 13 Pytest unit tests in `tests/`:
- `test_chat_engine.py`: Tests BM25 repetitive text saturation, vault index building, context search, and fallback synthesis.
- `test_concept_extractor.py`: Tests fallback regex concept extraction.
- `test_geojson_loader.py`: Tests GeoJSON loading, CRS validation, and feature mapping.
- `test_pdf_parser.py`: Tests classifier error handling, PyMuPDF extraction, and structure chunking.
- `test_vault_writer.py`: Tests filename sanitization and wikilink resolution.

All 13 unit tests pass cleanly in under 1 second (`pytest tests/ -v`).
