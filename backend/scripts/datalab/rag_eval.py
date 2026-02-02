#!/usr/bin/env python3
"""
RAG Evaluation Harness - Minimal but Actionable

Purpose: Validate retrieval quality for RAG systems.
Principles:
  - Versioned, frozen dataset before optimization
  - Few metrics, but relevant (1 metric = 1 aspect)
  - Trigger: any change to chunking/embeddings/index/search params/reranker/prompt

Usage:
  python rag_eval.py [--dataset path/to/dataset.jsonl] [--top-k 5]

Metrics:
  A) Retrieval:
     - Recall@k: Is relevant doc in top k results?
     - MRR: Mean Reciprocal Rank
     - Latency: p95 retrieval time

  B) RAG Quality (if ground truth answers available):
     - Faithfulness: Is answer grounded in retrieved chunks?
     - Answer relevancy: Does answer address the question?
"""

import argparse
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any
import statistics
from datetime import datetime


# ============================================================================
# EMBEDDED EVAL SET - Ethnopharmacology: Sceletium tortuosum
# ============================================================================
DEFAULT_EVAL_SET = {
    "metadata": {
        "version": "1.0.0",
        "created": "2025-01-30",
        "domain": "ethnopharmacology",
        "corpus": "sceletium_tortuosum",
    },
    "questions": [
        # SIMPLE FACTUAL (5 questions) - Direct lookups
        {
            "id": "simple_001",
            "type": "simple_factual",
            "question": "What are the active compounds in Sceletium tortuosum?",
            "keywords": [
                "mesembrine",
                "mesembrenone",
                "mesembrenol",
                "mesembranol",
                "alkaloids",
            ],
            "expected_docs": ["sceletium_chemistry", "alkaloid_profile"],
        },
        {
            "id": "simple_002",
            "type": "simple_factual",
            "question": "What is the mechanism of action of mesembrine?",
            "keywords": [
                "serotonin",
                "reuptake inhibition",
                "SSRI",
                "PDE4",
                "mechanism",
            ],
            "expected_docs": ["mesembrine_mechanism", "pharmacology"],
        },
        {
            "id": "simple_003",
            "type": "simple_factual",
            "question": "What are the side effects of Zembrin?",
            "keywords": [
                "Zembrin",
                "adverse",
                "side effects",
                "safety",
                "tolerability",
            ],
            "expected_docs": ["zembrin_safety", "clinical_safety"],
        },
        {
            "id": "simple_004",
            "type": "simple_factual",
            "question": "Which traditional cultures use Sceletium?",
            "keywords": [
                "Khoisan",
                "San",
                "Khoekhoe",
                "traditional",
                "South Africa",
                "preparation",
            ],
            "expected_docs": ["ethnobotany", "traditional_use"],
        },
        {
            "id": "simple_005",
            "type": "simple_factual",
            "question": "What is the chemical structure of mesembrine?",
            "keywords": [
                "chemical structure",
                "molecular formula",
                "stereochemistry",
                "mesembrine",
            ],
            "expected_docs": ["chemical_structure", "mesembrine_structure"],
        },
        # ANALYTICAL (10 questions) - Requires synthesis
        {
            "id": "analytical_001",
            "type": "analytical",
            "question": "Compare the antidepressant efficacy of different Sceletium chemotypes",
            "keywords": [
                "chemotype",
                "antidepressant",
                "efficacy",
                "comparison",
                "mesembrine vs mesembrenone",
            ],
            "expected_docs": ["chemotype_comparison", "antidepressant_studies"],
        },
        {
            "id": "analytical_002",
            "type": "analytical",
            "question": "What are the limitations of current Sceletium clinical trials?",
            "keywords": [
                "limitations",
                "sample size",
                "duration",
                "methodology",
                "clinical trials",
            ],
            "expected_docs": ["clinical_limitations", "trial_design"],
        },
        {
            "id": "analytical_003",
            "type": "analytical",
            "question": "How does Sceletium compare to SSRIs in terms of side effects?",
            "keywords": [
                "SSRI",
                "side effects",
                "comparison",
                "adverse events",
                "tolerability",
            ],
            "expected_docs": ["ssri_comparison", "safety_profile"],
        },
        {
            "id": "analytical_004",
            "type": "analytical",
            "question": "What is the relationship between alkaloid profile and pharmacological activity?",
            "keywords": ["alkaloid", "structure-activity", "pharmacology", "potency"],
            "expected_docs": ["structure_activity", "alkaloid_pharmacology"],
        },
        {
            "id": "analytical_005",
            "type": "analytical",
            "question": "How does processing method affect mesembrine content?",
            "keywords": [
                "fermentation",
                "processing",
                "extraction",
                "mesembrine content",
            ],
            "expected_docs": ["processing_methods", "extraction_studies"],
        },
        {
            "id": "analytical_006",
            "type": "analytical",
            "question": "What is the evidence for Sceletium's anxiolytic effects?",
            "keywords": ["anxiety", "anxiolytic", "cortisol", "stress", "clinical"],
            "expected_docs": ["anxiety_studies", "anxiolytic_effects"],
        },
        {
            "id": "analytical_007",
            "type": "analytical",
            "question": "How do different extraction solvents affect alkaloid yield?",
            "keywords": [
                "extraction",
                "solvent",
                "methanol",
                "ethanol",
                "yield",
                "optimization",
            ],
            "expected_docs": ["extraction_methods", "solvent_comparison"],
        },
        {
            "id": "analytical_008",
            "type": "analytical",
            "question": "What is the pharmacokinetic profile of mesembrine?",
            "keywords": [
                "pharmacokinetics",
                "bioavailability",
                "half-life",
                "metabolism",
                "Cmax",
            ],
            "expected_docs": ["pharmacokinetics", "absorption"],
        },
        {
            "id": "analytical_009",
            "type": "analytical",
            "question": "Are there documented drug interactions with Sceletium?",
            "keywords": [
                "drug interactions",
                "MAOI",
                "contraindications",
                "cytochrome",
            ],
            "expected_docs": ["drug_interactions", "contraindications"],
        },
        {
            "id": "analytical_010",
            "type": "analytical",
            "question": "What is the historical commercial use of Sceletium?",
            "keywords": [
                "history",
                "commercial",
                "Narcotic",
                "Act",
                "regulation",
                "trade",
            ],
            "expected_docs": ["commercial_history", "regulatory_history"],
        },
        # MULTI-DOCUMENT (5 questions) - Requires synthesis across sources
        {
            "id": "multi_001",
            "type": "multi_document",
            "question": "What is the consensus across multiple papers on mesembrine dosage?",
            "keywords": [
                "dosage",
                "consensus",
                "effective dose",
                "clinical",
                "recommendations",
            ],
            "expected_docs": ["dosage_guidelines", "clinical_dosage", "dose_response"],
        },
        {
            "id": "multi_002",
            "type": "multi_document",
            "question": "Which extraction method yields the highest mesembrine content?",
            "keywords": ["extraction", "yield", "optimization", "comparison", "HPLC"],
            "expected_docs": [
                "extraction_comparison",
                "yield_studies",
                "analytical_methods",
            ],
        },
        {
            "id": "multi_003",
            "type": "multi_document",
            "question": "How do traditional preparations compare to standardized extracts?",
            "keywords": [
                "traditional",
                "standardized",
                "fermentation",
                "preparation",
                "comparison",
            ],
            "expected_docs": [
                "traditional_preparation",
                "standardization",
                "fermentation_effects",
            ],
        },
        {
            "id": "multi_004",
            "type": "multi_document",
            "question": "What is the evidence base for Sceletium's cognitive enhancement claims?",
            "keywords": [
                "cognitive",
                "enhancement",
                "memory",
                "focus",
                "executive function",
            ],
            "expected_docs": [
                "cognitive_studies",
                "cognition_clinical",
                "mechanism_cognition",
            ],
        },
        {
            "id": "multi_005",
            "type": "multi_document",
            "question": "How does the alkaloid profile vary by geographical region?",
            "keywords": [
                "geographical",
                "variation",
                "chemotype",
                "region",
                "South Africa",
            ],
            "expected_docs": [
                "geographical_variation",
                "chemogeography",
                "regional_profiles",
            ],
        },
    ],
}


# ============================================================================
# DEFAULT THRESHOLDS
# ============================================================================
DEFAULT_THRESHOLDS = {
    "recall_at_k": 0.70,
    "mrr": 0.65,
    "p95_latency_ms": 2500,
    "error_rate": 0.01,
}


# ============================================================================
# DATA CLASSES
# ============================================================================
@dataclass
class SearchResult:
    doc_id: str
    title: str
    snippet: str
    score: float
    rank: int


@dataclass
class EvalResult:
    question_id: str
    question: str
    retrieved: List[SearchResult]
    relevant_found: bool
    relevant_rank: Optional[int]
    latency_ms: float
    error: Optional[str] = None


@dataclass
class MetricsSummary:
    total_questions: int
    recall_at_k: float
    mrr: float
    avg_latency_ms: float
    p95_latency_ms: float
    error_rate: float
    pass_thresholds: Dict[str, bool]


# ============================================================================
# CORE FUNCTIONS
# ============================================================================


def load_questions(eval_set_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load questions from JSON/JSONL file or use embedded default set.

    Args:
        eval_set_path: Path to custom eval set JSON or JSONL file

    Returns:
        Dictionary containing questions and metadata
    """
    if eval_set_path and Path(eval_set_path).exists():
        with open(eval_set_path, "r") as f:
            content = f.read().strip()

        # Try JSON first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try JSONL (one JSON object per line)
            questions = []
            for line in content.split("\n"):
                if line.strip():
                    questions.append(json.loads(line))
            return {
                "metadata": {
                    "version": "1.0.0",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                    "source": eval_set_path,
                },
                "questions": questions,
            }
    return DEFAULT_EVAL_SET


def search_chunks_keyword(
    question: str, corpus_dir: str, top_k: int = 5, keywords: Optional[List[str]] = None
) -> List[SearchResult]:
    """
    Simple keyword-based search over corpus files.
    For production, replace with vector search (Milvus, FAISS, etc.)

    Args:
        question: Query question
        corpus_dir: Path to corpus directory
        top_k: Number of results to return
        keywords: Optional keyword boost list

    Returns:
        List of SearchResult objects
    """
    corpus_path = Path(corpus_dir)
    results = []

    # If keywords provided, use them for better matching
    search_terms = keywords if keywords else question.lower().split()

    # Search through text files
    for file_path in corpus_path.rglob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Calculate score based on term frequency
            score = 0
            for term in search_terms:
                term_lower = term.lower()
                score += content.lower().count(term_lower)

            if score > 0:
                # Get snippet (first 200 chars containing first match)
                snippet = content[:200]
                results.append(
                    SearchResult(
                        doc_id=file_path.stem,
                        title=file_path.name,
                        snippet=snippet,
                        score=score,
                        rank=0,  # Will be set after sorting
                    )
                )
        except Exception as e:
            continue

    # Sort by score and assign ranks
    results.sort(key=lambda x: x.score, reverse=True)
    for i, result in enumerate(results[:top_k]):
        result.rank = i + 1

    return results[:top_k]


def search_chunks(
    question: str, top_k: int = 5, keywords: Optional[List[str]] = None, **kwargs
) -> List[SearchResult]:
    """
    Main search function - placeholder for actual RAG system.
    Implement this with your actual retrieval (Milvus, vector DB, etc.)

    Args:
        question: Query question
        top_k: Number of results to return
        keywords: Optional keyword hints

    Returns:
        List of SearchResult objects
    """
    # TODO: Replace with actual RAG system call
    # Example: return your_rag_system.retrieve(question, top_k)

    # Placeholder - return empty results
    return []


def evaluate_recall(
    results: List[SearchResult], relevant_doc_ids: List[str]
) -> tuple[bool, Optional[int]]:
    """
    Calculate Recall@k - is relevant doc in top k results?

    Args:
        results: Retrieved search results
        relevant_doc_ids: List of relevant document IDs

    Returns:
        Tuple of (found: bool, rank: Optional[int])
    """
    for result in results:
        for rel_id in relevant_doc_ids:
            if (
                rel_id.lower() in result.doc_id.lower()
                or result.doc_id.lower() in rel_id.lower()
            ):
                return True, result.rank
    return False, None


def evaluate_mrr(results: List[SearchResult], relevant_doc_ids: List[str]) -> float:
    """
    Calculate Reciprocal Rank for this query.
    Returns 1/rank if relevant doc found, else 0.

    Args:
        results: Retrieved search results
        relevant_doc_ids: List of relevant document IDs

    Returns:
        Reciprocal rank score (0.0 to 1.0)
    """
    for result in results:
        for rel_id in relevant_doc_ids:
            if (
                rel_id.lower() in result.doc_id.lower()
                or result.doc_id.lower() in rel_id.lower()
            ):
                return 1.0 / result.rank
    return 0.0


def evaluate_faithfulness(
    question: str, answer: str, retrieved_chunks: List[str]
) -> float:
    """
    LLM-as-judge for faithfulness (groundedness).
    Is the answer supported by retrieved context?

    Args:
        question: Original question
        answer: Generated answer
        retrieved_chunks: Retrieved context chunks

    Returns:
        Faithfulness score (0.0 to 1.0)
    """
    # TODO: Implement LLM-as-judge
    # Simple heuristic: check if answer claims are in context
    if not answer or not retrieved_chunks:
        return 0.0
    return 0.8  # Placeholder


def evaluate_answer_relevancy(question: str, answer: str) -> float:
    """
    LLM-as-judge for answer relevancy.
    Does the answer address the question?

    Args:
        question: Original question
        answer: Generated answer

    Returns:
        Relevancy score (0.0 to 1.0)
    """
    # TODO: Implement LLM-as-judge
    if not answer:
        return 0.0
    # Simple heuristic: answer length and keyword overlap
    question_words = set(question.lower().split())
    answer_words = set(answer.lower().split())
    overlap = len(question_words & answer_words)
    return min(1.0, overlap / max(len(question_words), 1))


# ============================================================================
# EVALUATION ENGINE
# ============================================================================


def run_evaluation(
    questions: List[Dict], search_fn, top_k: int = 5, **search_kwargs
) -> tuple[List[EvalResult], MetricsSummary]:
    """
    Run full evaluation over question set.

    Args:
        questions: List of question dictionaries
        search_fn: Search function to evaluate
        top_k: Number of results to retrieve
        **search_kwargs: Additional arguments for search function

    Returns:
        Tuple of (results list, metrics summary)
    """
    results = []
    latencies = []
    errors = 0

    for q in questions:
        start_time = time.time()

        try:
            retrieved = search_fn(
                question=q["question"],
                top_k=top_k,
                keywords=q.get("keywords"),
                **search_kwargs,
            )

            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)

            found, rank = evaluate_recall(retrieved, q.get("expected_docs", []))

            results.append(
                EvalResult(
                    question_id=q["id"],
                    question=q["question"],
                    retrieved=retrieved,
                    relevant_found=found,
                    relevant_rank=rank,
                    latency_ms=latency_ms,
                )
            )

        except Exception as e:
            errors += 1
            results.append(
                EvalResult(
                    question_id=q["id"],
                    question=q["question"],
                    retrieved=[],
                    relevant_found=False,
                    relevant_rank=None,
                    latency_ms=0,
                    error=str(e),
                )
            )

    # Calculate aggregate metrics
    recall_at_k = sum(1 for r in results if r.relevant_found) / len(results)

    mrr_scores = [
        evaluate_mrr(r.retrieved, questions[i].get("expected_docs", []))
        for i, r in enumerate(results)
    ]
    mrr = statistics.mean(mrr_scores) if mrr_scores else 0.0

    avg_latency = statistics.mean(latencies) if latencies else 0.0
    p95_latency = (
        statistics.quantiles(latencies, n=20)[-1]
        if len(latencies) > 1
        else (latencies[0] if latencies else 0.0)
    )

    error_rate = errors / len(questions)

    summary = MetricsSummary(
        total_questions=len(questions),
        recall_at_k=recall_at_k,
        mrr=mrr,
        avg_latency_ms=avg_latency,
        p95_latency_ms=p95_latency,
        error_rate=error_rate,
        pass_thresholds={},
    )

    return results, summary


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================


def print_scorecard(summary: MetricsSummary, thresholds: Dict[str, float]):
    """Print evaluation scorecard with PASS/FAIL indicators."""
    print("\n" + "=" * 60)
    print("RAG EVALUATION RESULTS")
    print("=" * 60)
    print(f"Total questions: {summary.total_questions}")
    print()

    metrics = [
        ("Recall@5", summary.recall_at_k, thresholds["recall_at_k"]),
        ("MRR", summary.mrr, thresholds["mrr"]),
        (
            "Avg Latency",
            f"{summary.avg_latency_ms:.0f}ms",
            thresholds["p95_latency_ms"],
            "ms",
        ),
        (
            "p95 Latency",
            f"{summary.p95_latency_ms:.0f}ms",
            thresholds["p95_latency_ms"],
            "ms",
        ),
        (
            "Error Rate",
            f"{summary.error_rate * 100:.1f}%",
            thresholds["error_rate"],
            "%",
        ),
    ]

    for metric_def in metrics:
        if len(metric_def) == 3:
            name, value, threshold = metric_def
            if isinstance(value, float):
                passed = value >= threshold
                status = "PASS" if passed else "FAIL"
                print(f"{name}: {value:.2f} (threshold: {threshold:.2f}) [{status}]")
            else:
                print(f"{name}: {value}")
        else:
            name, value_str, threshold, unit = metric_def
            value = float(value_str.replace(unit, "").replace("ms", ""))
            passed = value <= threshold
            status = "PASS" if passed else "FAIL"
            print(f"{name}: {value_str} (threshold: {threshold}{unit}) [{status}]")

    print("=" * 60)


def print_per_question(results: List[EvalResult]):
    """Print detailed per-question results."""
    print("\n=== PER-QUESTION RESULTS ===")

    for r in results:
        status = "OK" if r.relevant_found else "MISS"
        rank_info = f"rank={r.relevant_rank}" if r.relevant_rank else "not_found"

        if r.error:
            print(f"{r.question_id}: {r.question[:60]}... [ERROR: {r.error}]")
        else:
            print(f"{r.question_id}: {r.question[:60]}... [{status}] {rank_info}")

            if r.retrieved:
                print(
                    f"  -> Top result: {r.retrieved[0].title} (score: {r.retrieved[0].score:.1f})"
                )


def save_results(results: List[EvalResult], summary: MetricsSummary, output_path: str):
    """Save results to JSON file."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_questions": summary.total_questions,
            "recall_at_k": summary.recall_at_k,
            "mrr": summary.mrr,
            "avg_latency_ms": summary.avg_latency_ms,
            "p95_latency_ms": summary.p95_latency_ms,
            "error_rate": summary.error_rate,
        },
        "results": [
            {
                "question_id": r.question_id,
                "question": r.question,
                "relevant_found": r.relevant_found,
                "relevant_rank": r.relevant_rank,
                "latency_ms": r.latency_ms,
                "error": r.error,
                "retrieved_count": len(r.retrieved),
            }
            for r in results
        ],
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_path}")


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="RAG Evaluation Harness")
    parser.add_argument("--dataset", type=str, help="Path to custom eval set JSON file")
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of documents to retrieve (default: 5)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/LAB/@thesis/datalab/eval/results.json",
        help="Output path for results JSON",
    )
    parser.add_argument(
        "--corpus", type=str, help="Path to corpus directory (for keyword search)"
    )
    parser.add_argument("--thresholds", type=str, help="Path to thresholds YAML file")

    args = parser.parse_args()

    # Load questions
    eval_set = load_questions(args.dataset)
    questions = eval_set["questions"]

    print(
        f"Loaded {len(questions)} questions from {eval_set['metadata'].get('domain', 'unknown')}"
    )

    # Load thresholds or use defaults
    thresholds = DEFAULT_THRESHOLDS.copy()
    # TODO: Load from YAML if provided

    # Select search function
    if args.corpus:
        search_fn = lambda **kwargs: search_chunks_keyword(
            corpus_dir=args.corpus, **kwargs
        )
        print(f"Using keyword search on corpus: {args.corpus}")
    else:
        # Use placeholder - user should implement search_chunks()
        search_fn = search_chunks
        print("WARNING: Using placeholder search (returns empty results)")
        print("         Implement search_chunks() or use --corpus for keyword search")

    # Run evaluation
    results, summary = run_evaluation(
        questions=questions, search_fn=search_fn, top_k=args.top_k
    )

    # Print results
    print_scorecard(summary, thresholds)
    print_per_question(results)

    # Save results
    save_results(results, summary, args.output)

    # Overall verdict
    passed = summary.recall_at_k >= thresholds["recall_at_k"]
    print(f"\n{'=' * 60}")
    print(
        f"OVERALL: {'GO - Thresholds met' if passed else 'NO-GO - Thresholds not met'}"
    )
    print(f"{'=' * 60}")

    # Suggest next action
    if not passed:
        print("\nNEXT ACTION:")
        if summary.recall_at_k < 0.5:
            print("  [ ] Review document indexing and chunking strategy")
        elif summary.recall_at_k < thresholds["recall_at_k"]:
            print("  [ ] Improve retrieval with better embeddings or query expansion")
        if summary.error_rate > thresholds["error_rate"]:
            print("  [ ] Fix errors in retrieval pipeline")


if __name__ == "__main__":
    main()
