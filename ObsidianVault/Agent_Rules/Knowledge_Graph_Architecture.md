# Knowledge Graph Architecture

## Storage model
The knowledge graph **is** the Obsidian vault: a folder of markdown files
linked with `[[wikilinks]]`. No separate graph database (see
`Decision_Log.md`).

## Vault folder taxonomy
```
vault/
  datasets/          # one note per ingested dataset/report
  concepts/          # extracted concepts/topics, linked from datasets
  locations/          # place/region notes, linked from GeoJSON features
  organizations/       # agencies, contributors, data owners
  _templates/          # note templates used by the vault writer
```

## Note schema
Every generated note starts with YAML frontmatter:

```yaml
---
title: <human-readable title>
type: dataset | concept | location | organization
source_file: <original filename>
source_format: pdf | geojson
ingested_at: <ISO date>
tags: [air-quality, water, ...]
---
```

Body: a short auto-generated summary, followed by `[[wikilinks]]` to related
concepts/locations/datasets, and any extracted tables/figures as embedded
content or linked attachments.

## Linking rules
- A dataset note links to every concept/location it mentions.
- A location note links back to every dataset that references it (Obsidian
  backlinks handle this automatically — no need to write it both ways).
- Concepts link to related concepts only when the ingestion pipeline finds an
  explicit relationship (e.g. shared taxonomy term) — no speculative linking.

## Discovery beyond explicit links (proposed improvement)
Wikilinks only capture relationships the ingestion pipeline explicitly wrote.
For discovery across notes that *should* be related but weren't explicitly
linked (e.g. two reports on the same pollutant using different terminology),
consider adding an optional semantic-search index (embeddings) over the vault
as a second, non-authoritative discovery layer — surfaced in the Streamlit
app as "related notes you might have missed," not written back into the vault
as links. This keeps the vault itself as clean, human-auditable ground truth.

## Versioning / re-ingestion
When a source document is re-ingested (updated NEA report), the vault writer
updates the existing note in place rather than creating a duplicate, keyed on
`source_file`. Decision on how conflicts/edits made directly in Obsidian are
preserved is open — see `Roadmap.md`.
