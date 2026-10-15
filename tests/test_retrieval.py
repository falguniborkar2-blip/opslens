from pathlib import Path

import pytest

from opslens.providers import FakeProvider
from opslens.rag import Index
from opslens.rag.bm25 import BM25, tokenize
from opslens.rag.index import rrf


def test_tokenize_keeps_technical_terms() -> None:
    assert "systemctl" in tokenize("Run systemctl daemon-reload now")
    assert "daemon-reload" in tokenize("Run systemctl daemon-reload now")
    assert "the" not in tokenize("the service")


def test_bm25_prefers_matching_doc() -> None:
    bm = BM25(["kubernetes pod crash", "disk is full", "selinux denial"])
    scores = bm.scores("pod crash")
    assert scores.index(max(scores)) == 0


def test_rrf_rewards_agreement() -> None:
    fused = rrf([[0, 1, 2], [1, 0, 2]])
    assert fused[0] == fused[1] > fused[2]


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("pod stuck in CrashLoopBackOff", "k8s-crashloopbackoff"),
        ("deleted file but df still shows full", "disk-space"),
        ("getenforce shows Enforcing and httpd is denied", "selinux"),
        ("ImagePullBackOff from private registry", "k8s-image-pull"),
    ],
)
def test_corpus_search(corpus_index: Index, question: str, expected: str) -> None:
    hits = corpus_index.search(question, k=3)
    assert hits[0].chunk.doc_id == expected


def test_hybrid_and_roundtrip(corpus_index: Index, tmp_path: Path) -> None:
    fake = FakeProvider()
    idx = Index.build(corpus_index.chunks, fake.embed)
    hits = idx.search("OOM killer killed my process", k=3, mode="hybrid", embedder=fake.embed)
    assert "memory-oom" in [h.chunk.doc_id for h in hits]
    idx.save(tmp_path / "i.json")
    loaded = Index.load(tmp_path / "i.json")
    assert loaded.embeddings is not None and len(loaded.chunks) == len(idx.chunks)


def test_dense_requires_embeddings(corpus_index: Index) -> None:
    with pytest.raises(ValueError):
        corpus_index.search("x", mode="dense")
