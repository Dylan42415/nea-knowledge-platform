# PDF Ingestion

## Library choices
- **Docling** (primary) — layout-aware parsing, high-fidelity table and
  reading-order extraction, active maintenance, permissive license.
- **PyMuPDF / PyMuPDF4LLM** — fast first-pass text/metadata/image extraction;
  used where Docling's fuller pipeline is unnecessary overhead.
- **Camelot + Tesseract** — fallback for table-heavy scanned pages needing OCR.

Rationale and alternatives considered (Unstructured, Marker, LlamaParse,
pdfmux) are logged in `Decision_Log.md`.

## Pipeline stages
1. **Classify** — text-native vs scanned (routes to OCR or not).
2. **Extract** — text, tables, images, metadata via the library chosen above.
3. **Chunk** — structure-aware chunking (by section/heading, not fixed token
   windows), preserving tables/figures as distinct chunks with captions.
4. **Concept extraction** — identify candidate concepts/locations/orgs per
   chunk (method TBD — see `Roadmap.md`).
5. **Write to vault** — one dataset note per document, per
   `Knowledge_Graph_Architecture.md` schema, linking to any concept/location
   notes found in step 4.

## Table handling
Tables are the highest-risk element (layout errors cascade into garbled
content). Docling's table extraction is the default; Camelot is the fallback
for cases Docling misses. Every extracted table is kept as a distinct chunk
with its caption, not flattened into surrounding prose.

## Error handling
- A page that fails extraction is logged and skipped, not silently dropped —
  the dataset note records "N pages failed extraction" so it's visible.
- No retry-forever loops; failures surface for manual review.
