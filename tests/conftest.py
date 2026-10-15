from __future__ import annotations

from pathlib import Path

import pytest

from opslens.config import Settings
from opslens.rag import Index, load_corpus

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def corpus_index() -> Index:
    return Index.build(load_corpus(ROOT / "data" / "docs"))


@pytest.fixture
def settings() -> Settings:
    s = Settings()
    s.rag.mode = "bm25"
    s.rag.top_k = 3
    return s
