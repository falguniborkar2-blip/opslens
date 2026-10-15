"""Markdown-aware chunking: split on headings first, then by size with overlap."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.M)


@dataclass
class Chunk:
    id: str  # "<doc_id>#<n>"
    doc_id: str  # file stem, e.g. "systemd-troubleshooting"
    title: str  # document title (first H1)
    section: str  # nearest heading
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _slug(path: Path) -> str:
    return path.stem.lower()


def _split_sections(md: str) -> list[tuple[str, str]]:
    """Return (heading, body) pairs. Text before the first heading gets heading ''."""
    matches = list(_HEADING.finditer(md))
    if not matches:
        return [("", md.strip())]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0 and md[: matches[0].start()].strip():
        sections.append(("", md[: matches[0].start()].strip()))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        body = md[m.end() : end].strip()
        if body:
            sections.append((m.group(2), body))
    return sections


def _window(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    if overlap >= size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    pieces, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        # Prefer to break on a paragraph or sentence boundary.
        if end < len(text):
            cut = max(text.rfind("\n\n", start, end), text.rfind(". ", start, end))
            if cut > start + size // 2:
                end = cut + 1
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [p for p in pieces if p]


def chunk_markdown(md: str, doc_id: str, size: int = 800, overlap: int = 120) -> list[Chunk]:
    h1 = re.search(r"^#\s+(.+)$", md, re.M)
    title = h1.group(1).strip() if h1 else doc_id
    chunks: list[Chunk] = []
    for heading, body in _split_sections(md):
        for piece in _window(body, size, overlap):
            text = f"{heading}\n{piece}" if heading else piece
            chunks.append(Chunk(f"{doc_id}#{len(chunks)}", doc_id, title, heading or title, text))
    return chunks


def load_corpus(docs_dir: Path, size: int = 800, overlap: int = 120) -> list[Chunk]:
    files = sorted(p for p in docs_dir.rglob("*") if p.suffix in {".md", ".txt"})
    if not files:
        raise FileNotFoundError(f"no .md/.txt documents found in {docs_dir}")
    chunks: list[Chunk] = []
    for path in files:
        chunks.extend(chunk_markdown(path.read_text(encoding="utf-8"), _slug(path), size, overlap))
    return chunks
