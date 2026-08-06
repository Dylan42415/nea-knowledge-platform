# Decision Log

## 2026-08-06 — Vault-only storage, no graph database
**Decision:** The Obsidian vault (markdown + wikilinks on disk) is the sole
source of truth for the knowledge graph.
**Alternatives considered:**
- Hybrid: vault + Memgraph/Neo4j for querying/analytics.
- Graph DB as source of truth, vault auto-generated as a view.
**Why chosen:** Simplest option that meets the stated need (human navigation
via Obsidian); avoids running/maintaining a database for a v1. Revisit if
query needs outgrow what wikilinks + Obsidian search can do.
**Future implications:** No Cypher-style querying available; any graph
analytics (centrality, clustering) would read the vault directly via
NetworkX rather than a live database.

## 2026-08-06 — PDF ingestion: Docling + PyMuPDF
**Decision:** Docling as primary parser (tables/layout), PyMuPDF/PyMuPDF4LLM
for fast first-pass text extraction, Camelot+Tesseract as OCR/table fallback.
**Alternatives considered:** Unstructured (cloud API, job-size limits not
ideal for batch NEA volume), Marker, LlamaParse (paid, LLM-based), pdfmux
(newer, strong benchmark numbers but less established).
**Why chosen:** Actively maintained, permissive license, modular, no
per-file cloud limits.
**Future implications:** If table accuracy proves insufficient in practice,
pdfmux is the logged fallback to evaluate first.

## 2026-08-06 — GeoJSON: leafmap + pydeck
**Decision:** leafmap as the primary mapping layer, pydeck used directly for
3D/large-layer cases.
**Alternatives considered:** streamlit-folium (simpler, less capable), raw
folium (no native Streamlit support).
**Why chosen:** Native Streamlit support, multiple backends, direct
GeoJSON/GeoPandas compatibility.
**Future implications:** Streamlit Community Cloud's 1GB RAM limit (if used
for deployment) constrains dataset size without tiling/simplification.
