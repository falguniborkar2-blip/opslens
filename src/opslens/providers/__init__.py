"""LLM provider plug-ins. Add a new backend by implementing `LLMProvider`."""

from __future__ import annotations

from ..config import LLMConfig
from .base import ChatResponse, LLMProvider, Message, ProviderError, ToolCall
from .fake import FakeProvider
from .openai_compat import OpenAICompatibleProvider

__all__ = [
    "ChatResponse",
    "FakeProvider",
    "LLMProvider",
    "Message",
    "OpenAICompatibleProvider",
    "ProviderError",
    "ToolCall",
    "build_provider",
]


def build_provider(cfg: LLMConfig) -> LLMProvider:
    if cfg.provider == "fake":
        return FakeProvider()
    return OpenAICompatibleProvider(
        base_url=cfg.base_url,
        model=cfg.model,
        api_key=cfg.api_key,
        embedding_model=cfg.embedding_model,
        temperature=cfg.temperature,
        timeout_s=cfg.timeout_s,
    )
