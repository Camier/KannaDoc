"""
Embedding utilities for vector normalization.

This module provides common utilities for handling multi-vector embeddings
from ColQwen and similar visual embedding models.
"""
from typing import List, Union


def normalize_multivector(emb) -> List[List[float]]:
    """
    Normalize multi-vector embeddings to a consistent format.

    Returns List[List[float]] shaped (n_tokens, dim)

    Accepts:
      - List[List[float]]                     -> as-is
      - List[ List[List[float]] ] with len=1  -> emb[0]
      - List[float]                           -> [emb]

    Args:
        emb: Raw embedding data from the embedding model

    Returns:
        List[List[float]]: Normalized multi-vector embeddings

    Raises:
        TypeError: If the embedding structure is not recognized

    Examples:
        >>> normalize_multivector([[0.1, 0.2], [0.3, 0.4]])
        [[0.1, 0.2], [0.3, 0.4]]

        >>> normalize_multivector([[[0.1, 0.2], [0.3, 0.4]]])
        [[0.1, 0.2], [0.3, 0.4]]

        >>> normalize_multivector([0.1, 0.2, 0.3])
        [[0.1, 0.2, 0.3]]
    """
    if not isinstance(emb, list):
        raise TypeError(f"Unexpected embedding type: {type(emb)}")

    if len(emb) == 0:
        return []

    # Case: list-of-embeddings for each input text, single input
    if (
        len(emb) == 1
        and isinstance(emb[0], list)
        and emb[0]
        and isinstance(emb[0][0], list)
    ):
        emb = emb[0]

    # Case: single vector
    if emb and isinstance(emb[0], (float, int)):
        return [[float(x) for x in emb]]

    # Case: multivector
    if emb and isinstance(emb[0], list):
        return [[float(x) for x in v] for v in emb]

    raise TypeError("Unexpected embedding structure")


__all__ = ["normalize_multivector"]
