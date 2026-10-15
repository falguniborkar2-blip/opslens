"""Provider-agnostic types for chat completion with tool calling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class ChatResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ProviderError(RuntimeError):
    """Raised when an LLM backend fails or returns something unusable."""


class LLMProvider(Protocol):
    """Any LLM backend OpsLens can talk to."""

    name: str

    def chat(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> ChatResponse: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...
