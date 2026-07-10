"""Local embedding model wrapper for the demo backend."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.config import settings


class EmbeddingServiceError(RuntimeError):
    """Raised when the local embedding model cannot be loaded or called."""


@lru_cache(maxsize=1)
def _model() -> Any:
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(settings.embed_model)
    except ImportError as exc:
        raise EmbeddingServiceError(
            "The 'sentence-transformers' package is required for /debug/embed."
        ) from exc
    except Exception as exc:
        raise EmbeddingServiceError(
            f"Failed to load embedding model {settings.embed_model!r}."
        ) from exc


def embed(texts: list[str]) -> np.ndarray:
    """Return normalized embeddings as a two-dimensional numpy array."""

    if not texts:
        raise EmbeddingServiceError("At least one text is required for embedding.")

    try:
        import numpy as np

        vectors = _model().encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
    except EmbeddingServiceError:
        raise
    except Exception as exc:
        raise EmbeddingServiceError("Embedding request failed.") from exc

    return np.asarray(vectors, dtype=np.float32)
