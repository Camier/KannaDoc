# LAYRA (KannaDoc) - Agent Knowledge Base

Academic research fork for thesis work on retrieval evaluation and visual RAG optimization.

## 1. PROJECT OVERVIEW

| Aspect | Details |
|--------|---------|
| **Purpose** | Ethnopharmacology RAG system with evaluation framework |
| **Corpus** | 129 PDFs with legacy-migrated V2 entities (re-extraction recommended) |
| **Stack** | FastAPI + Milvus + MiniMax M2.1 (Neo4j disabled) |
| **Upstream** | [liweiphys/layra](https://github.com/liweiphys/layra) |

## 2. DIRECTORY STRUCTURE

```text
layra/
├── backend/
│   ├── app/                    # FastAPI application
│   │   ├── api/endpoints/      # REST endpoints
│   │   │   └── eval.py         # Evaluation API
│   │   └── eval/               # Evaluation system
│   │       ├── metrics.py      # MRR, NDCG, P@K, R@K
│   │       ├── labeler.py      # LLM relevance scoring
│   │       ├── runner.py       # Orchestration + p95 latency
│   │       └── config/thresholds.yaml
│   │
│   ├── lib/
│   │   ├── entity_extraction/  # V2 extraction (MiniMax M2.1)
│   │   │   ├── schemas.py      # 15 entity types, 6 relationships
│   │   │   ├── extractor.py    # MinimaxExtractor
│   │   │   ├── prompt.py       # Extraction prompt
│   │   │   └── AGENTS.md       # Module docs
│   │   └── datalab/            # Archived DataLab modules
│   │       ├── datalab_api.py  # DataLab API client
│   │       ├── milvus_ingest.py
│   │       ├── neo4j_ingest.py
│   │       └── ...
│   │
│   ├── scripts/
│   │   └── datalab/            # Ingestion & extraction scripts
│   │       ├── extract_entities_v2.py   # V2 entity extraction CLI
│   │       ├── migrate_entities_v2.py   # V1→V2 migration
│   │       ├── milvus_ingest.py         # Vector ingestion
│   │       ├── neo4j_ingest.py          # Graph ingestion
│   │       └── ...
│   │
│   └── data/
│       ├── pdfs/               # 129 source PDFs
│       ├── extractions/        # 129 docs with V2 entities
│       ├── id_mapping.json     # doc_id ↔ file_id
│       ├── .minimax_api_key
│       └── .datalab_api_key
│
├── frontend/                   # React frontend (from upstream)
├── README.md
└── AGENTS.md                   # This file
```

## 3. ENTITY EXTRACTION (V2)

**Status**: Entities are **legacy-migrated** from V1 format. Fresh extraction with MiniMax M2.1 is recommended. Relationships are not yet populated.

15 entity types across 5 domains (schema designed for MiniMax M2.1):

| Domain | Types |
|--------|-------|
| Ethnographic | Culture, TraditionalUse, Preparation |
| Botanical | Taxon, PlantPart, RawMaterial |
| Chemical | CompoundClass, Compound, Concentration |
| Pharmacological | Target, Mechanism, PharmEffect |
| Clinical | Indication, Evidence, Study |

6 relationship types: `TRANSFORMS`, `CONTAINS`, `ACTS_ON`, `PRODUCES`, `TREATS`, `SUGGESTS` (not yet extracted)

**Detailed docs**: `backend/lib/entity_extraction/AGENTS.md`  
**Audit report**: `backend/docs/PIPELINE_AUDIT_2026-02-02.md`

## 4. CANONICAL COMMANDS

```bash
cd /LAB/@thesis/layra/backend

# Entity extraction
PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py --test "Quercetin inhibits COX-2"
PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py --input-dir data/extractions

# Milvus ingestion
PYTHONPATH=. python3 scripts/datalab/milvus_ingest.py --input-dir data/extractions

# Neo4j ingestion
PYTHONPATH=. python3 scripts/datalab/neo4j_ingest.py --input-dir data/extractions

# Run evaluation
curl -X POST http://localhost:8000/api/v1/eval/run -d '{"dataset_id": "...", "config": {"top_k": 5}}'
```

## 5. INFRASTRUCTURE

| Service | Purpose | Notes |
|---------|---------|-------|
| **MiniMax M2.1** | Entity extraction | API key in `data/.minimax_api_key` |
| **Milvus** | Vector store | HNSW index, configurable M/efConstruction |
| **Neo4j** | Knowledge graph | **DISABLED** (not deployed) |
| **FastAPI** | Backend API | Eval endpoints at `/api/v1/eval/` |

## 6. EVALUATION SYSTEM

Quality thresholds (`backend/app/eval/config/thresholds.yaml`):
- Recall@5 ≥ 0.70
- MRR ≥ 0.65
- p95 latency ≤ 2500ms

## 7. HISTORY

| Date | Event |
|------|-------|
| 2026-01 | Forked LAYRA, added eval system |
| 2026-02-01 | Migrated 129 docs to V2 entity format |
| 2026-02-02 | Created entity_extraction module with MiniMax |
| 2026-02-02 | Archived DataLab → consolidated into LAYRA |

## 8. CROSS-REFERENCES

- `README.md`: User-facing documentation
- `backend/lib/entity_extraction/AGENTS.md`: Extraction module details
- `/LAB/@thesis/datalab.archive/`: Original DataLab (archived)
