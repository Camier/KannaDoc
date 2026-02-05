# DataLab Pipeline Documentation

This directory contains documentation for the DataLab extraction pipeline that feeds data into LAYRA.

## Pipeline Elements

| Document | Purpose |
|----------|---------|
| [PIPELINE_OVERVIEW.md](PIPELINE_OVERVIEW.md) | Root knowledge base, architecture, data flow |
| [CORE_LIBRARY.md](CORE_LIBRARY.md) | Python modules for extraction and normalization |
| [RAG_PIPELINE.md](RAG_PIPELINE.md) | Chunking, indexing, and evaluation |
| [API_REFERENCE.md](API_REFERENCE.md) | DataLab Marker API documentation index |
| [DATA_SCHEMAS.md](DATA_SCHEMAS.md) | Pydantic models and JSON structures |
| [ENTITY_EXTRACTION.md](ENTITY_EXTRACTION.md) | Gemini-based NER extraction |

## Data Flow: DataLab → LAYRA

```
DataLab/ALL_FLAT/ (129 PDFs)
         │
         ▼
   Marker API Extraction
         │
         ▼
DataLab/data/extractions/prod_max/
├── <doc_id>/
│   ├── normalized.json    # NormalizedDocumentV2
│   ├── entities.json      # Gemini NER output
│   └── render/            # HTML, MD, images
         │
         ▼
LAYRA/backend/data/
├── corpus/
│   ├── biblio_corpus.jsonl      # 129 bibliographic records
│   ├── chunks_corpus.jsonl      # 29,638 RAG chunks
│   └── images_manifest.json     # 1,565 image assets
├── extractions/                 # 129 doc directories (copied)
├── metadata/
│   └── paper_catalog.jsonl      # DOI/citekey metadata
└── id_mapping.json              # doc_id ↔ file_id (129 entries)
```

## Key Integration Points

| Component | Location | Usage |
|-----------|----------|-------|
| ID Mapping | `backend/data/id_mapping.json` | Link DataLab doc_id to LAYRA file_id |
| Entities | `backend/data/extractions/*/entities.json` | NER: Compound, Plant, Effect, Disease, Dosage |
| Chunks | `backend/data/corpus/chunks_corpus.jsonl` | RAG text chunks with metadata |
| Images | `backend/data/corpus/images_manifest.json` | Image asset catalog |

## Source Repository

**DataLab Location**: `/LAB/@thesis/datalab`

| Directory | Contents |
|-----------|----------|
| `ALL_FLAT/` | 129 source PDFs (READ-ONLY) |
| `lib/` | Core Python modules |
| `scripts/` | Ingestion and extraction scripts |
| `data/extractions/prod_max/` | Production extractions |
| `datalab_doc/` | Scraped API documentation |

## Quick Commands

```bash
# Entity extraction (parallel)
cd /LAB/@thesis/datalab
python3 scripts/entity_extract_gemini.py \
  --input-dir data/extractions/prod_max \
  --doc-workers 12 \
  --chunk-workers 4

# Verify integration
python3 scripts/verify_merge.py

# Check ID mapping
python3 -c "import json; m=json.load(open('/LAB/@thesis/layra/backend/data/id_mapping.json')); print(f'{len(m)} mappings')"
```

## Infrastructure

| Service | Endpoint | Purpose |
|---------|----------|---------|
| CLIProxyAPI | `http://localhost:8317/v1` | Gemini API proxy |
| Milvus | `localhost:19530` | Vector database |
| Neo4j | `bolt://localhost:7687` | Graph database |

---

**Last Updated**: 2026-02-02  
**Source**: `/LAB/@thesis/datalab/AGENTS.md`
