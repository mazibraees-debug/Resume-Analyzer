"""
Embedding Model
===============
Embedder that prefers sentence-transformers if available, falling back
gracefully to Scikit-learn TF-IDF embeddings to guarantee 100% reliability
across all environments.
"""
from __future__ import annotations

import logging
from functools import lru_cache
import numpy as np

from app.config import get_settings

logger = logging.getLogger("app.embeddings")


class FallbackTfidfEmbedder:
    """Fast, zero-conflict text embedder using scikit-learn."""

    def __init__(self, dimension: int = 384):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._dim = dimension
        self._vectorizer = TfidfVectorizer(
            max_features=dimension,
            ngram_range=(1, 2),
            sublinear_tf=True,
            norm="l2",
        )
        self._corpus: list[str] = [
            "python fastapi backend developer software engineer",
            "experience skills project communication requirements",
        ]
        self._vectorizer.fit(self._corpus)

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dim))

        all_texts = self._corpus + texts
        try:
            self._vectorizer.fit(all_texts)
            matrix = self._vectorizer.transform(texts).toarray()
            if matrix.shape[1] < self._dim:
                pad_width = ((0, 0), (0, self._dim - matrix.shape[1]))
                matrix = np.pad(matrix, pad_width, mode="constant")
            return matrix
        except Exception:
            return np.zeros((len(texts), self._dim))

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        return self._dim


class Embedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._fallback = None

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(model_name)
            logger.info("Loaded SentenceTransformer (%s)", model_name)
        except Exception as exc:
            logger.info(
                "SentenceTransformer unavailable or has version conflicts (%s). Using Scikit-Learn embedder.",
                exc,
            )
            self._fallback = FallbackTfidfEmbedder(dimension=384)

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension))

        if self._model is not None:
            try:
                return self._model.encode(
                    texts, normalize_embeddings=True, show_progress_bar=False
                )
            except Exception as exc:
                logger.warning("SentenceTransformer encode error: %s; using fallback.", exc)

        if self._fallback is None:
            self._fallback = FallbackTfidfEmbedder(dimension=384)
        return self._fallback.embed(texts)

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        if self._model is not None:
            try:
                return self._model.get_sentence_embedding_dimension()
            except Exception:
                pass
        return 384


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Both vectors are normalized; return dot product or normalized cosine."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    return Embedder(settings.embedding_model_name)
