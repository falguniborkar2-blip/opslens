"""Searchable index over chunks: BM25, dense embeddings, or hybrid (Reciprocal Rank Fusion)."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

from .bm25 import BM25
from .chunker import Chunk

Embedder = Callable[[list[str]], list[list[float]]]
Mode = Literal["bm25", "dense", "hybrid"]


@dataclass
class Hit:
    chunk: Chunk
    score: float


def _rank(scores: list[float] | np.ndarray) -> list[int]:
    return sorted(range(len(scores)), key=lambda i: -float(scores[i]))


def rrf(rankings: list[list[int]], k: int = 60) -> dict[int, float]:
    """Reciprocal Rank Fusion (Cormack et al., 2009)."""
    fused: dict[int, float] = {}
    for ranking in rankings:
        for r, idx in enumerate(ranking):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + r + 1)
    return fused


class Index:
    def __init__(self, chunks: list[Chunk], embeddings: np.ndarray | None = None) -> None:
        if not chunks:
            raise ValueError("cannot build an index with no chunks")
        self.chunks = chunks
        self.bm25 = BM25([c.text for c in chunks])
        self.embeddings = embeddings
        if embeddings is not None:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            self.embeddings = embeddings / np.clip(norms, 1e-12, None)

    @classmethod
    def build(cls, chunks: list[Chunk], embedder: Embedder | None = None, batch: int = 32) -> Index:
        emb = None
        if embedder is not None:
            vecs: list[list[float]] = []
            for i in range(0, len(chunks), batch):
                vecs.extend(embedder([c.text for c in chunks[i : i + batch]]))
            emb = np.asarray(vecs, dtype=np.float32)
        return cls(chunks, emb)

    def search(
        self, query: str, k: int = 4, mode: Mode = "bm25", embedder: Embedder | None = None
    ) -> list[Hit]:
        rankings: list[list[int]] = []
        bm25_scores = self.bm25.scores(query)
        if mode in ("bm25", "hybrid"):
            rankings.append([i for i in _rank(bm25_scores) if bm25_scores[i] > 0])
        if mode in ("dense", "hybrid"):
            if self.embeddings is None or embedder is None:
                raise ValueError(f"mode={mode!r} needs an index built with embeddings")
            q = np.asarray(embedder([query])[0], dtype=np.float32)
            q /= max(float(np.linalg.norm(q)), 1e-12)
            rankings.append(_rank(self.embeddings @ q))
        if mode == "bm25":
            order = rankings[0][:k]
            return [Hit(self.chunks[i], float(bm25_scores[i])) for i in order]
        fused = rrf(rankings)
        order = sorted(fused, key=lambda i: -fused[i])[:k]
        return [Hit(self.chunks[i], fused[i]) for i in order]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunks": [c.to_dict() for c in self.chunks],
            "embeddings": None if self.embeddings is None else self.embeddings.tolist(),
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Index:
        payload = json.loads(path.read_text(encoding="utf-8"))
        chunks = [Chunk(**c) for c in payload["chunks"]]
        emb = payload.get("embeddings")
        return cls(chunks, None if emb is None else np.asarray(emb, dtype=np.float32))
