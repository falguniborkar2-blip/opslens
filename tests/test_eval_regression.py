"""Quality gate: CI fails if retrieval quality regresses below the recorded baseline."""

from pathlib import Path

from opslens.eval.runner import evaluate, load_questions
from opslens.rag import Index

QUESTIONS = Path(__file__).resolve().parents[1] / "eval" / "questions.yaml"


def test_bm25_quality_gate(corpus_index: Index) -> None:
    res = evaluate(corpus_index, load_questions(QUESTIONS), mode="bm25", k=3)
    assert res.n >= 30
    assert res.recall_at_k >= 0.90
    assert res.mrr >= 0.80
