# KannaDoc

> **Academic Research Fork** of [LAYRA](https://github.com/liweiphys/layra) for thesis research on retrieval evaluation and visual RAG optimization.

---

## About This Repository

This is a **private research fork** used for academic thesis work. It extends the original LAYRA project with:

- **Retrieval Evaluation System** - Batch evaluation with IR metrics (MRR, NDCG, Precision@K, Recall@K)
- **LLM-based Relevance Labeling** - Automated ground truth generation for evaluation datasets
- **Thesis-specific Corpus** - 129 academic documents indexed for research
- **Neo4j Status** - Knowledge graph storage is currently **DISABLED** (not deployed)
- **Extended API** - Evaluation endpoints under `/api/v1/eval/`
- **Entity Extraction V3.1** - 17 entity types, 16 relationships via GLM-4.7 via Z.ai (glm-4.7-flash)
- **Self-Contained Corpus** - 129 PDFs + 129 extractions consolidated from DataLab

## Repository Structure

This repository consolidates:
- **LAYRA** (upstream fork) - RAG application framework
- **DataLab** (archived) - PDF extraction pipeline → now in `backend/lib/datalab/` and `backend/scripts/datalab/`

## Key Extensions

### Retrieval Evaluation (`/api/v1/eval/`)

```bash
# Create evaluation dataset
POST /api/v1/eval/datasets
{
  "name": "eval-v1",
  "kb_id": "...",
  "query_count": 50
}

# Run evaluation
POST /api/v1/eval/run
{
  "dataset_id": "...",
  "config": {"top_k": 5}
}

# Get metrics
GET /api/v1/eval/runs/{run_id}
# Returns: MRR, NDCG@K, Precision@K, Recall@K
```

### Directory Structure

```
backend/
├── app/                    # FastAPI application
│   ├── api/endpoints/      # REST endpoints
│   │   ├── eval.py         # Evaluation endpoints
│   │   └── knowledge_base.py # KB management (Upload/Delete/List)
│   └── eval/               # Evaluation system
│       ├── metrics.py      # IR metrics (MRR, NDCG, P@K, R@K)
│       ├── labeler.py      # LLM relevance scoring
│       ├── query_generator.py
│       ├── dataset.py
│       ├── runner.py       # Evaluation orchestration + p95 latency
│       └── config/
│           └── thresholds.yaml
│
├── lib/                    # Core libraries
│   ├── entity_extraction/  # V3.1 entity extraction (GLM-4.7 via Z.ai)
│   │   ├── schemas.py      # 17 entity types, 16 relationships
│   │   ├── extractor.py    # GLM (Z.ai) + MiniMax fallback
│   │   └── prompt.py       # Extraction prompt
│   └── datalab/            # DataLab pipeline (archived from datalab.archive)
│       ├── datalab_api.py  # DataLab API client (Marker API)
│       ├── datalab_process.py# PDF-to-block transformation
│       ├── datalab_ingest.py # Document catalog manager
│       └── ...
│
├── scripts/
│   └── datalab/            # Ingestion & extraction scripts
│       ├── extract_entities_v2.py
│       ├── milvus_ingest.py
│       ├── neo4j_ingest.py  # (Neo4j disabled in current deployment)
│       └── ...
│
└── data/
    ├── pdfs/               # 129 source PDFs (corpus)
    ├── extractions/        # 129 docs with V2 entities
    ├── id_mapping.json     # doc_id ↔ file_id mapping
    ├── .minimax_api_key    # MiniMax API key (fallback)
    └── .datalab_api_key    # DataLab API key
```

### Entity Extraction V3.1

GLM-4.7 (via Z.ai) extraction with 17 entity types across 6 domains.

**Available Models:**
- `glm-4.7-flash` (default) - Fastest inference
- `glm-4.7` - Standard model
- `glm-4.5-air` - Alternative option

**Configuration:**
- API Key: `ZAI_API_KEY` environment variable
- Fallback: MiniMax M2.1 (use `--provider minimax`)

| Domain | Types |
|--------|-------------|
| Ethnographic | Culture, UseRecord, TraditionalUse, Preparation |
| Botanical | Taxon, PlantPart, RawMaterial |
| Chemical | CompoundClass, Compound |
| Pharmacological | Target, Effect |
| Clinical | Condition, Evidence, Study, Dosage, AdverseEvent |
| Product | Product |

```bash
# Extract entities from a document (GLM via Z.ai default)
cd backend
PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py --test "Quercetin inhibits COX-2"

# Use MiniMax fallback
PYTHONPATH=. python3 scripts/datalab/extract_entities_v2.py --provider minimax --test "Quercetin inhibits COX-2"
```

See `backend/lib/entity_extraction/AGENTS.md` for full documentation.

### RAG Pipeline Improvements (2026-02)

Recent enhancements to the RAG pipeline for thesis evaluation:

| Feature | Description |
|---------|-------------|
| **Retry Logic** | Tenacity-based retry on Milvus search (3 attempts, exponential backoff 2-30s) |
| **Configurable HNSW** | `HNSW_M` and `HNSW_EF_CONSTRUCTION` now configurable via environment |
| **p95 Latency Tracking** | Evaluation runs now include p95 latency metrics in milliseconds |
| **Quality Thresholds** | `thresholds.yaml` with pass/fail targets (recall≥0.70, MRR≥0.65, p95≤2500ms) |

**Configuration** (add to `.env`):
```bash
HNSW_M=48                    # HNSW M parameter (4-64, default: 48)
HNSW_EF_CONSTRUCTION=1024    # HNSW efConstruction (≥8, default: 1024)
```

## Original Project

For the full LAYRA project with complete documentation, visit:
- **Repository**: [liweiphys/layra](https://github.com/liweiphys/layra)
- **Documentation**: [liweiphys.github.io/layra](https://liweiphys.github.io/layra)

## License

This fork inherits the [Apache 2.0 License](./LICENSE) from the original LAYRA project.

---

*This repository is for academic research purposes only and is not intended for public distribution.*
