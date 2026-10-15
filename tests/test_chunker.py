import pytest

from opslens.rag.chunker import _window, chunk_markdown

MD = """# Title

Intro text.

## Section A
Alpha content.

## Section B
Beta content.
"""


def test_splits_on_headings_and_keeps_title() -> None:
    chunks = chunk_markdown(MD, "doc")
    assert [c.section for c in chunks] == ["Title", "Section A", "Section B"]
    assert all(c.title == "Title" for c in chunks)
    assert chunks[1].text.startswith("Section A\n")
    assert [c.id for c in chunks] == ["doc#0", "doc#1", "doc#2"]


def test_window_overlaps_and_covers_text() -> None:
    text = " ".join(f"word{i}." for i in range(400))
    pieces = _window(text, size=300, overlap=50)
    assert len(pieces) > 1
    assert all(len(p) <= 300 for p in pieces)
    assert pieces[-1].endswith("word399.")


def test_window_rejects_bad_overlap() -> None:
    with pytest.raises(ValueError):
        _window("x" * 100, size=10, overlap=10)
