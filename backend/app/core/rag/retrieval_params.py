"""Shared retrieval parameter normalization.

This module is intentionally dependency-light so it can be reused from:
- ChatService (SSE chat RAG)
- knowledge-base search-preview endpoint (debug UI)

Goal: avoid drift where one path enforces thesis-safe minimums (e.g. top_k>=50
in sparse/dual modes) while the other accidentally caps recall.
"""

from __future__ import annotations


def normalize_top_k(
    top_k: int,
    *,
    retrieval_mode: str,
    default_top_k: int,
    top_k_cap: int,
    sparse_min_k: int,
) -> int:
    """Normalize top_k with thesis-safe minimums for sparse/dual retrieval modes.

    Conventions:
    - top_k == -1 is a sentinel meaning "use environment default".
    - Always clamp to [1, top_k_cap].
    - In sparse_then_rerank / dual_then_rerank, enforce sparse_min_k to avoid
      accidental tiny recall (e.g. legacy UI defaults).
    """
    try:
        top_k_i = int(top_k)
    except Exception:
        top_k_i = -1

    try:
        top_k_cap_i = int(top_k_cap)
    except Exception:
        top_k_cap_i = 120

    if top_k_i == -1:
        normalized = int(default_top_k)
    elif top_k_i < 1:
        normalized = 1
    else:
        normalized = top_k_i

    if retrieval_mode in ("sparse_then_rerank", "dual_then_rerank"):
        try:
            min_k = int(sparse_min_k)
        except Exception:
            min_k = 50
        if normalized < min_k:
            normalized = min_k

    if normalized > top_k_cap_i:
        normalized = top_k_cap_i
    return normalized

