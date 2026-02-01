# KannaDoc

> **Academic Research Fork** of [LAYRA](https://github.com/liweiphys/layra) for thesis research on retrieval evaluation and visual RAG optimization.

---

## About This Repository

This is a **private research fork** used for academic thesis work. It extends the original LAYRA project with:

- **Retrieval Evaluation System** - Batch evaluation with IR metrics (MRR, NDCG, Precision@K, Recall@K)
- **LLM-based Relevance Labeling** - Automated ground truth generation for evaluation datasets
- **Thesis-specific Corpus** - 129 academic documents indexed for research
- **Extended API** - Evaluation endpoints under `/api/v1/eval/`

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

### Files Added

```
backend/app/eval/
├── metrics.py          # IR metrics (MRR, NDCG, P@K, R@K)
├── labeler.py          # LLM relevance scoring
├── query_generator.py  # Query synthesis
├── dataset.py          # Dataset management
└── runner.py           # Evaluation orchestration

backend/app/api/endpoints/
└── eval.py             # REST API endpoints
```

## Original Project

For the full LAYRA project with complete documentation, visit:
- **Repository**: [liweiphys/layra](https://github.com/liweiphys/layra)
- **Documentation**: [liweiphys.github.io/layra](https://liweiphys.github.io/layra)

## License

This fork inherits the [Apache 2.0 License](./LICENSE) from the original LAYRA project.

---

*This repository is for academic research purposes only and is not intended for public distribution.*
