"""
Vector Store
============
Lightweight, high-performance in-memory vector store powered by NumPy
embeddings and cosine similarity. Provides an identical interface to
ChromaDB without requiring C++ compilation or external build tools.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import numpy as np

from app.config import get_settings
from app.embeddings.embedder import get_embedder, cosine_similarity


@dataclass
class RetrievedChunk:
    text: str
    similarity: float


class VectorStore:
    def __init__(self):
        self._collections: dict[str, list[dict]] = {}
        self._embedder = get_embedder()

    def new_collection(self) -> str:
        """Create a fresh collection for one application run, return its name."""
        name = f"cv_{uuid.uuid4().hex[:12]}"
        self._collections[name] = []
        return name

    def add_cv_chunks(self, collection_name: str, chunks: list[str]) -> None:
        """Embed and store CV chunks in the given collection."""
        if not chunks:
            return
        if collection_name not in self._collections:
            self._collections[collection_name] = []

        embeddings = self._embedder.embed(chunks)
        for i, chunk in enumerate(chunks):
            self._collections[collection_name].append({
                "id": f"chunk-{i}",
                "text": chunk,
                "embedding": embeddings[i],
            })

    def query_similar(
        self, collection_name: str, query_text: str, top_k: int = 3
    ) -> list[RetrievedChunk]:
        """Return the top_k CV chunks most similar to query_text."""
        items = self._collections.get(collection_name, [])
        if not items:
            return []

        query_vec = self._embedder.embed_one(query_text)
        scored: list[RetrievedChunk] = []

        for item in items:
            sim = cosine_similarity(query_vec, item["embedding"])
            scored.append(RetrievedChunk(text=item["text"], similarity=float(sim)))

        # Sort descending by similarity
        scored.sort(key=lambda r: r.similarity, reverse=True)
        return scored[:top_k]

    def delete_collection(self, collection_name: str) -> None:
        """Drop the collection when application run completes."""
        self._collections.pop(collection_name, None)


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
