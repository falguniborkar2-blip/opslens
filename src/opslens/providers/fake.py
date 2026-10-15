"""Deterministic provider used in tests and CI (no model or network needed)."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from typing import Any

from .base import ChatResponse, Message

Script = Callable[[list[Message], list[dict[str, Any]] | None], ChatResponse]


def _default_script(messages: list[Message], tools: list[dict[str, Any]] | None) -> ChatResponse:
    # Echo the first cited context passage so tests can check grounding.
    context = next((m.content for m in messages if m.role == "system" and "[1]" in m.content), "")
    match = re.search(r"\[1\][^\n]*\n(.+?)(?:\n\[2\]|\Z)", context, re.S)
    snippet = match.group(1).strip()[:200] if match else "I don't know."
    return ChatResponse(content=f"{snippet} [1]")


class FakeProvider:
    name = "fake"

    def __init__(self, script: Script | None = None, dim: int = 64) -> None:
        self.script = script or _default_script
        self.dim = dim
        self.calls: list[list[Message]] = []

    def chat(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> ChatResponse:
        self.calls.append(list(messages))
        return self.script(messages, tools)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Hashing-trick bag-of-words embeddings: cheap, deterministic, roughly semantic."""
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for tok in re.findall(r"[a-z0-9]+", text.lower()):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0
            out.append(vec)
        return out
