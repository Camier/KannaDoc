# KannaDoc

> **Academic Research Fork** of [LAYRA](https://github.com/liweiphys/layra) for thesis research on retrieval evaluation and visual RAG optimization.

---

## About This Repository

This is a **private research fork** used for academic thesis work. It extends the original LAYRA project with:

- **Retrieval Evaluation System** - Batch evaluation with IR metrics (MRR, NDCG, Precision@K, Recall@K)
- **LLM-based Relevance Labeling** - Automated ground truth generation for evaluation datasets
- **Thesis-specific Corpus** - Academic documents indexed for research (see `AGENTS.md` for current counts)
- **Neo4j Status** - Knowledge graph storage is currently **DISABLED** (not deployed)
- **Extended API** - Evaluation endpoints under `/api/v1/eval/`
- **Entity Extraction V3.1** - 17 entity types, 16 relationships via DeepSeek (deepseek-chat)
- **Self-Contained Corpus** - PDFs + extractions consolidated from DataLab (see `AGENTS.md` for current counts)

**Consolidated overview:** `docs/IMPORTANT_REPO_OVERVIEW.md`

## Operations Notes (Thesis Fork)

- Vector DB stack (default): docker-compose Milvus (`milvus-standalone` + `milvus-etcd` + `milvus-minio`).
- Backend health: `curl -sf http://localhost:8090/api/v1/health/ready | python3 -m json.tool`
- Milvus host->docker migration runbook: `docs/operations/MILVUS_HOST_TO_DOCKER_MIGRATION.md`
- **Kafka consumer must be running** for file uploads to be embedded into Milvus. If the consumer is down, uploads succeed (files saved to MinIO) but embedding silently never happens. Check: `docker compose ps kafka-consumer`.

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
│           ├── thresholds.yaml
│           └── ground_truth.json
│
├── lib/                    # Core libraries
│   ├── entity_extraction/  # V3.1 entity extraction (DeepSeek path)
│   │   ├── schemas.py      # 17 entity types, 16 relationships
│   │   ├── extractor.py    # V3.1 extraction logic
│   │   └── prompt.py       # Extraction prompt
│   └── datalab/            # DataLab pipeline (archived from datalab.archive)
│       ├── datalab_api.py  # DataLab API client (Marker API)
│       ├── datalab_process.py# PDF-to-block transformation
│       ├── datalab_ingest.py # Document catalog manager
│       └── ...
│
├── scripts/
│   └── datalab/            # Ingestion & extraction scripts
│       ├── extract_deepseek.py
│       ├── milvus_ingest.py
│       └── ...
│
└── data/
    ├── pdfs/               # Source PDFs (corpus; see AGENTS.md for counts)
    ├── extractions/        # Extraction folders with V3.1 entities
    ├── id_mapping.json     # doc_id ↔ file_id mapping
    ├── .minimax_api_key    # MiniMax API key (fallback)
    └── .datalab_api_key    # DataLab API key
```

### Entity Extraction V3.1

DeepSeek extraction (thesis reproducibility path) with 17 entity types across 6 domains.

**Pinned Model:**
- `deepseek-chat`

**Configuration:**
- API Key: `DEEPSEEK_API_KEY` environment variable

| Domain | Types |
|--------|-------------|
| Ethnographic | Culture, UseRecord, TraditionalUse, Preparation |
| Botanical | Taxon, PlantPart, RawMaterial |
| Chemical | CompoundClass, Compound |
| Pharmacological | Target, Effect |
| Clinical | Condition, Evidence, Study, Dosage, AdverseEvent |
| Product | Product |

```bash
# Extract entities from a document (DeepSeek)
cd backend
PYTHONPATH=. python3 scripts/datalab/extract_deepseek.py --test "Quercetin inhibits COX-2"
```

See `backend/lib/entity_extraction/AGENTS.md` for full documentation.

### RAG Pipeline Improvements (2026-02)

Recent enhancements to the RAG pipeline for thesis evaluation:

| Feature | Description |
|---------|-------------|
| **Retry Logic** | Tenacity-based retry on Milvus search (3 attempts, exponential backoff 2-30s) |
| **Configurable HNSW** | `HNSW_M` and `HNSW_EF_CONSTRUCTION` now configurable via environment |
| **p95 Latency Tracking** | Evaluation runs now include p95 latency metrics in milliseconds |
| **MaxSim Aggregation** | `rag_eval.py` uses MaxSim scoring for multi-vector ColQwen queries |
| **Ground Truth Mapping** | `rag_eval.py --ground-truth` loads question_id to doc_id mapping from `backend/app/eval/config/ground_truth.json` |
| **Quality Thresholds** | `thresholds.yaml` with pass/fail targets (recall>=0.70, MRR>=0.65, p95<=2500ms) |

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
