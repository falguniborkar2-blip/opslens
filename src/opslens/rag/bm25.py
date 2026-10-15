"""Okapi BM25 implemented from scratch (no external search engine needed)."""

from __future__ import annotations

import math
import re
from collections import Counter

_STOP = frozenset(
    (
        "a an and are as at be by can do does for from how i if in is it its of on or "
        "my me the this that to what when where which why with you your"
    ).split()
)


def tokenize(text: str) -> list[str]:
    return [
        t
        for t in re.findall(r"[a-z0-9][a-z0-9_.\-]*[a-z0-9]|[a-z0-9]", text.lower())
        if t not in _STOP
    ]


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.tfs = [Counter(tokenize(d)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = (sum(self.lens) / len(self.lens)) if self.lens else 0.0
        df: Counter[str] = Counter()
        for tf in self.tfs:
            df.update(tf.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        out = []
        for tf, dl in zip(self.tfs, self.lens, strict=True):
            s = 0.0
            for term in q:
                f = tf.get(term)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                s += self.idf[term] * f * (self.k1 + 1) / denom
            out.append(s)
        return out
