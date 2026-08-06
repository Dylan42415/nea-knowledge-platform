# Roadmap

## Phase 0 — Research (done)
- Evaluated PDF ingestion, GeoJSON/mapping, and knowledge-graph tooling.
- Decided: Obsidian vault as sole graph store (no separate DB).
- Docs scaffolded (this set).

## Phase 1 — Ingestion MVP
- PDF pipeline: Docling + PyMuPDF, basic chunking, vault note output.
- GeoJSON pipeline: leafmap load/validate, location note output.
- Fixture-based tests per `Testing.md`.

## Phase 2 — Concept extraction & linking
- Method for identifying concepts/relationships within chunks (open —
  candidates: keyword/taxonomy matching first, LLM-assisted extraction if
  needed later).
- Wikilink generation between datasets, concepts, locations.

## Phase 3 — Streamlit app
- Browse/search view over the vault.
- Map view (GeoJSON layers) linked into vault notes.
- Graph view (embed or link out to Obsidian graph).

## Phase 4 — Scale & polish
- Re-ingestion/update handling for changed source documents.
- Performance work for large geo datasets (tiling/simplification).
- Optional semantic-search discovery layer (see
  `Knowledge_Graph_Architecture.md`).

## Open questions
- How are manual edits made directly in Obsidian preserved across
  re-ingestion of the same source file?
- What triggers re-ingestion (manual, scheduled, watch-folder)?
