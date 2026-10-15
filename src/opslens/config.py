"""Configuration loading: YAML file + environment variable overrides.

Precedence (highest first): environment variables (OPSLENS_*), YAML file, defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: Literal["openai_compatible", "fake"] = "openai_compatible"
    # Ollama exposes an OpenAI-compatible API under /v1, so the same provider works for
    # Ollama, vLLM, OpenAI, Groq, etc.
    base_url: str = "http://localhost:11434/v1"
    model: str = "llama3.2:3b"
    embedding_model: str | None = "nomic-embed-text"
    api_key: str | None = None
    temperature: float = 0.1
    timeout_s: float = 120.0


class RAGConfig(BaseModel):
    docs_dir: Path = Path("data/docs")
    index_path: Path = Path("data/index.json")
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4
    mode: Literal["bm25", "dense", "hybrid"] = "bm25"


class MCPConfig(BaseModel):
    enabled: bool = True
    # Command used to launch the MCP server over stdio.
    command: str = "python"
    args: list[str] = Field(default_factory=lambda: ["-m", "opslens.tools.mcp_server"])
    max_tool_rounds: int = 3


class Settings(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    system_prompt: str = (
        "You are OpsLens, a careful assistant for Linux and Kubernetes operations. "
        "Answer using the provided documentation context and tool results. "
        "Cite sources as [n] using the numbers of the context passages. "
        "If the context does not contain the answer, say so instead of guessing. "
        "Never suggest destructive commands without a clear warning."
    )


_ENV_MAP: dict[str, tuple[str, str]] = {
    "OPSLENS_LLM_PROVIDER": ("llm", "provider"),
    "OPSLENS_LLM_BASE_URL": ("llm", "base_url"),
    "OPSLENS_LLM_MODEL": ("llm", "model"),
    "OPSLENS_LLM_API_KEY": ("llm", "api_key"),
    "OPSLENS_EMBEDDING_MODEL": ("llm", "embedding_model"),
    "OPSLENS_RAG_MODE": ("rag", "mode"),
    "OPSLENS_RAG_TOP_K": ("rag", "top_k"),
    "OPSLENS_MCP_ENABLED": ("mcp", "enabled"),
}


def load_settings(path: str | Path | None = None) -> Settings:
    data: dict[str, Any] = {}
    cfg_path = Path(path or os.environ.get("OPSLENS_CONFIG", "config.yaml"))
    if cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    for env, (section, key) in _ENV_MAP.items():
        if env in os.environ:
            data.setdefault(section, {})[key] = os.environ[env]
    return Settings.model_validate(data)
