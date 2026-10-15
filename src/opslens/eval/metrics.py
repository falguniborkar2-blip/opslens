"""Standard IR metrics for evaluating the retriever."""

from __future__ import annotations

from collections.abc import Sequence


def dedupe(ranked: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(ranked))


def recall_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    return len(set(ranked[:k]) & relevant) / len(relevant) if relevant else 0.0


def reciprocal_rank(ranked: Sequence[str], relevant: set[str]) -> float:
    return next((1.0 / r for r, d in enumerate(ranked, 1) if d in relevant), 0.0)


def average_precision_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    hits, total = 0, 0.0
    for r, d in enumerate(ranked[:k], 1):
        if d in relevant:
            hits += 1
            total += hits / r
    return total / min(len(relevant), k) if relevant else 0.0
