"""Run retrieval evaluation over a labelled question set."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import yaml

from ..rag.index import Embedder, Index, Mode
from .metrics import average_precision_at_k, dedupe, recall_at_k, reciprocal_rank


@dataclass
class EvalResult:
    mode: str
    n: int
    recall_at_1: float
    recall_at_k: float
    mrr: float
    map_at_k: float
    k: int
    failures: list[str]

    def row(self) -> str:
        return (
            f"| {self.mode:<6} | {self.n:>3} | {self.recall_at_1:.3f} | {self.recall_at_k:.3f}"
            f" | {self.mrr:.3f} | {self.map_at_k:.3f} |"
        )


def load_questions(path: Path) -> list[dict[str, object]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(data["questions"])


def evaluate(
    index: Index,
    questions: list[dict[str, object]],
    mode: Mode = "bm25",
    k: int = 3,
    embedder: Embedder | None = None,
) -> EvalResult:
    r1, rk, rr, ap, fails = [], [], [], [], []
    for q in questions:
        text = str(q["question"])
        relevant = set(map(str, q["relevant"]))  # type: ignore[call-overload]
        hits = index.search(text, k=k * 5, mode=mode, embedder=embedder)
        ranked = dedupe([h.chunk.doc_id for h in hits])
        r1.append(recall_at_k(ranked, relevant, 1))
        rk.append(recall_at_k(ranked, relevant, k))
        rr.append(reciprocal_rank(ranked, relevant))
        ap.append(average_precision_at_k(ranked, relevant, k))
        if not set(ranked[:k]) & relevant:
            fails.append(text)
    return EvalResult(mode, len(questions), mean(r1), mean(rk), mean(rr), mean(ap), k, fails)
