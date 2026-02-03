"""BGE-M3 sparse embedding service for hybrid search."""

from FlagEmbedding import BGEM3FlagModel
from typing import Any, Dict, List, cast
import torch


class BGEM3Service:
    """BGE-M3 model service for sparse embeddings."""

    def __init__(self, model_path: str = "/model_weights/bge-m3"):
        """Initialize BGE-M3 model.

        Args:
            model_path: Path to model weights or HuggingFace model name
        """
        self.model_path = model_path
        self.model: Any = None

    def warmup(self):
        """Load model and run warmup inference."""
        print(f"Loading BGE-M3 from {self.model_path}...")
        model = BGEM3FlagModel(
            self.model_path,
            use_fp16=torch.cuda.is_available(),
            device="cuda" if torch.cuda.is_available() else "cpu",
        )
        if model is None:
            raise RuntimeError("BGE-M3 model failed to load.")
        self.model = model
        # Warmup inference
        _ = model.encode(["warmup query"], return_sparse=True)
        print("BGE-M3 ready")

    def encode_sparse(self, texts: List[str]) -> List[Dict[int, float]]:
        """Generate sparse embeddings for texts.

        Args:
            texts: List of text strings to encode

        Returns:
            List of sparse vectors as {token_id: weight} dicts
        """
        if not texts:
            return []

        if self.model is None:
            raise RuntimeError("BGE-M3 model is not loaded. Call warmup() first.")
        model = cast(BGEM3FlagModel, self.model)

        # Handle empty strings
        results = []
        non_empty_indices = []
        non_empty_texts = []

        for i, text in enumerate(texts):
            if not text or not text.strip():
                results.append({})
            else:
                non_empty_indices.append(i)
                non_empty_texts.append(text)
                results.append(None)  # Placeholder

        if non_empty_texts:
            # Get sparse embeddings from BGE-M3
            output = model.encode(non_empty_texts, return_sparse=True)
            sparse_vecs = output.get("lexical_weights", output.get("sparse_vecs", []))

            for idx, sparse_vec in zip(non_empty_indices, sparse_vecs):
                # Convert to {int: float} format
                if isinstance(sparse_vec, dict):
                    results[idx] = {int(k): float(v) for k, v in sparse_vec.items()}
                else:
                    results[idx] = {}

        return results


# Singleton instance
bge_m3 = BGEM3Service()
