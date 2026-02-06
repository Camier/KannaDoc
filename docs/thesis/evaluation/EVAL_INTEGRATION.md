# Evaluation Integration Guide

This guide describes the evaluation system for the LAYRA ethnopharmacology RAG system, covering metric definitions, configuration, and usage.

## 1. Metrics Overview

The system uses standard Information Retrieval (IR) metrics to quantify retrieval quality and system performance.

### 1.1 Mean Reciprocal Rank (MRR)
MRR measures the quality of the ranking for the first relevant result. It is the average of the reciprocal ranks of the first relevant document for each query.

**Formula:**
$$MRR = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{rank_i}$$
*Where $rank_i$ is the rank position of the first relevant document for query $i$. If no relevant document is found, the reciprocal rank is 0.*

### 1.2 Normalized Discounted Cumulative Gain (NDCG)
NDCG measures ranking quality by penalizing relevant results lower in the list, accounting for the position of all relevant documents.

**Formula:**
$$NDCG = \frac{DCG}{IDCG}$$
*Where $DCG = \sum_{i=1}^{k} \frac{rel_i}{\log_2(i+1)}$ and $IDCG$ is the $DCG$ of the ideal ranking.*

### 1.3 Precision@K
The proportion of retrieved documents in the top $K$ that are relevant.

**Formula:**
$$Precision@K = \frac{\text{relevant\_in\_top\_k}}{K}$$

### 1.4 Recall@K
The proportion of all relevant documents that were found in the top $K$ results.

**Formula:**
$$Recall@K = \frac{\text{relevant\_in\_top\_k}}{\text{total\_relevant}}$$

### 1.5 p95 Latency
The 95th percentile query time, indicating that 95% of queries complete within this duration. This is used to track system responsiveness under load.

---

## 2. Configuration

Thresholds for evaluation are defined in `backend/app/eval/config/thresholds.yaml`.

### Threshold Values
The system defines different bars for development and production stages:

| Metric | Development Target | Production Target |
|--------|--------------------|-------------------|
| Recall@5 | ≥ 0.60 | ≥ 0.80 |
| MRR | ≥ 0.50 | ≥ 0.75 |
| p95 Latency | ≤ 5000ms | ≤ 2000ms |
| Error Rate | ≤ 1% | ≤ 0.5% |

### Configuration File
```yaml
retrieval:
  recall_at_k: 0.70
  mrr: 0.65
  p95_latency_ms: 2500
  error_rate: 0.01

stages:
  development:
    recall_at_k: 0.60
    mrr: 0.50
    p95_latency_ms: 5000
  production:
    recall_at_k: 0.80
    mrr: 0.75
    p95_latency_ms: 2000
```

---

## 3. Usage Guide

### 3.1 CLI Evaluation
The `rag_eval.py` script provides a command-line interface for running evaluations.

**Basic Usage:**
```bash
# Run evaluation with default settings
PYTHONPATH=. python3 scripts/datalab/rag_eval.py --top-k 5

# Run against a specific Milvus collection
PYTHONPATH=. python3 scripts/datalab/rag_eval.py --collection my_collection --top-k 10

# Use a custom ground truth mapping
PYTHONPATH=. python3 scripts/datalab/rag_eval.py --ground-truth app/eval/config/ground_truth.json
```

**Common Arguments:**
- `--dataset`: Path to custom evaluation set (JSON/JSONL).
- `--top-k`: Number of documents to retrieve per query.
- `--output`: Path to save results JSON.
- `--collection`: Milvus collection name for vector search.

### 3.2 LLM-based Relevance Labeling
The system supports automated ground truth generation and relevance scoring using LLM-as-a-judge patterns (implemented in `backend/app/eval/labeler.py`).

**Process:**
1. **Query Generation**: Synthetic queries are generated based on document chunks.
2. **Retrieval**: The RAG system retrieves candidates for the generated queries.
3. **Relevance Labeling**: An LLM (DeepSeek or Zhipu GLM-4) evaluates the relevance of retrieved chunks against the query on a scale (e.g., 0-3) or binary basis.
4. **Metric Calculation**: The labels are used as ground truth to calculate the IR metrics described in Section 1.

---

## 4. API Reference
For detailed documentation on evaluation REST endpoints (e.g., `/api/v1/eval/run`), please refer to `docs/API.md`.
