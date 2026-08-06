# Architecture

## Purpose
NEA knowledge management platform. Ingests PDFs and GeoJSON, converts them into
an interconnected Obsidian vault (markdown + wikilinks), and exposes a Streamlit
app for browsing, search, and graph exploration.

## Storage decision
The vault (plain markdown files + wikilinks on disk) is the single source of
truth for the knowledge graph. No separate graph database. See
`Decision_Log.md` for the reasoning and alternatives considered.

## High-level components

```
             +-------------------+
  PDFs  ---> |  PDF Ingestion    | ---+
             +-------------------+    |
                                       v
             +-------------------+   +----------------------+
 GeoJSON --> |  GeoJSON Pipeline | ->|  Vault Writer         |
             +-------------------+   |  (notes + wikilinks + |
                                       |   frontmatter)        |
                                       +-----------+-----------+
                                                    |
                                                    v
                                       +----------------------+
                                       |  Obsidian Vault (fs)  |
                                       +-----------+-----------+
                                                    |
                                       +-----------v-----------+
                                       |  Streamlit App         |
                                       |  - search / browse     |
                                       |  - graph view          |
                                       |  - map view (GeoJSON)  |
                                       +------------------------+
```

## Folder structure (proposed)

```
project/
  docs/                  # this documentation set
  vault/                 # the Obsidian vault (generated + curated notes)
  src/
    ingestion/
      pdf/               # Docling / PyMuPDF wrappers
      geojson/            # leafmap / pydeck wrappers
    vault_writer/         # note + wikilink + frontmatter generation
    app/                 # Streamlit app
  tests/
```

## Key libraries (see research notes in Decision_Log.md)
- PDF: Docling (primary), PyMuPDF/PyMuPDF4LLM (fast text pass)
- GeoJSON/maps: leafmap (Streamlit-native, multi-backend), pydeck for 3D layers
- Graph: none — Obsidian's own graph view + wikilinks; NetworkX only if/when
  offline analysis (centrality, clustering) is needed, reading directly from
  vault frontmatter — not a persisted database

## Note format (vault)
Each ingested document/dataset becomes one or more markdown notes with YAML
frontmatter (source file, ingestion date, dataset type, tags) and `[[wikilinks]]`
to related concepts, locations, and other datasets. Full schema in
`Knowledge_Graph_Architecture.md`.

## Non-goals (current phase)
- No authentication/multi-user access control yet
- No real-time ingestion (batch only)
- No custom graph query language — navigation is via Obsidian links/graph view
