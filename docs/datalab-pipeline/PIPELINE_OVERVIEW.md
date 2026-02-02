# DataLab Pipeline Overview

Document processing pipeline for academic PDFs (ethnopharmacology) using DataLab Marker API. Prepares RAG-ready outputs for Milvus + Neo4j dual indexing.

## Pipeline Stages

1. **INGEST**: SHA256 hashing and cataloging (`lib/datalab_ingest.py`)
2. **EXTRACT**: Marker API processing (`lib/datalab_process.py`, `lib/batch_extractor.py`)
3. **NORMALIZE**: Raw → structured transformation (`lib/normalization.py`)
4. **REPAIR**: Metadata enrichment (`lib/repair/`). Year/DOI backfill via CrossRef
5. **ENTITY EXTRACTION**: Gemini NER (`scripts/entity_extract_gemini.py`)
6. **INDEX**: Dual ingestion to Milvus (vectors) + Neo4j (graph)

## Directory Structure

```text
/LAB/@thesis/datalab/
├── ALL_FLAT/              # Source corpus: 129 PDFs (READ-ONLY)
├── data/
│   ├── catalog.json       # SHA256 -> file mapping
│   ├── extractions/prod_max/  # Production extractions (129 docs)
│   ├── corpus/            # Aggregated outputs
│   │   ├── biblio_corpus.jsonl
│   │   ├── chunks_corpus.jsonl
│   │   └── images_manifest.json
│   ├── logs/              # Centralized logs
│   └── notes/             # Schema definitions
├── lib/                   # Core Python modules
│   ├── schemas/           # Pydantic models
│   ├── normalization.py   # Raw → Normalized transformation
│   ├── block_index.py     # Block indexing + anchor resolution
│   └── repair/            # Metadata backfill
├── scripts/               # Ingestion scripts
│   ├── milvus_ingest.py   # Vector DB ingestion
│   ├── neo4j_ingest.py    # Graph DB ingestion
│   ├── entity_extract_gemini.py  # Gemini-based NER (parallel)
│   ├── aggregate_corpus.py       # Corpus aggregation
│   └── verify_merge.py    # LAYRA integration verification
└── datalab_doc/           # Scraped API documentation
```

## Canonical Commands

```bash
# Full extraction (129 PDFs, 2-4 hours)
python3 -m lib.batch_extractor \
  --mode full \
  --schema data/notes/page_schema_ethnopharmacology.json \
  --output-dir data/extractions/prod_max

# Entity extraction (parallel, ~1-2 hours)
python3 scripts/entity_extract_gemini.py \
  --input-dir data/extractions/prod_max \
  --doc-workers 12 \
  --chunk-workers 4

# Corpus aggregation
python3 scripts/aggregate_corpus.py

# Dual ingestion
python3 scripts/milvus_ingest.py --source normalized --input data/extractions/prod_max
python3 scripts/neo4j_ingest.py --input data/extractions/prod_max
```

## Infrastructure

| Service | Connection | Notes |
|---------|------------|-------|
| Neo4j | `bolt://localhost:7687` | NO AUTH (Desktop mode) |
| Milvus | `localhost:19530` | Collection: `ethnopharmacology_v2` |
| Datalab API | `https://www.datalab.to/api/v1/` | Key in `data/.datalab_api_key` |
| CLIProxyAPI | `http://localhost:8317/v1` | Key: `layra-cliproxyapi-key` |

## Image Extraction

Images come from TWO sources (merged in `normalize_document()`):
1. **Top-level**: `result.images` = `{filename: base64}` (may be None)
2. **Per-block**: `result.json.children[N].images` = `{filename: base64}`

The `collect_images_from_json()` function walks the Marker JSON tree to collect all per-block images.

## Conventions

- **Hashing**: SHA256 only. Never MD5.
- **Atomic Writes**: Write to `.tmp`, then `os.replace()`.
- **Path Security**: Use `sanitize_path_component()` for all user input.
- **Images**: Persist to `_assets/<doc_id>/images/<sha256>.<ext>`.
- **Block IDs**: Format `/page/N/BlockType/M` (0-indexed pages).

## Anti-Patterns

- No `except Exception:` - catch specific errors.
- No emojis in logs or data files.
- Never modify `ALL_FLAT/` (read-only source).
- Never hard-code paths; use `DATALAB_ROOT` env var.
