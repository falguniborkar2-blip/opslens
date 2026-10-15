"""The assistant loop: guardrails -> retrieve -> LLM (+ MCP tool calls) -> answer with sources."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .config import Settings
from .conversation import ConversationStore
from .guardrails import check_question, find_placeholder_args, redact_secrets
from .providers.base import LLMProvider, Message
from .rag.index import Hit, Index
from .tools.mcp_client import ToolBox

log = logging.getLogger("opslens")


@dataclass
class Source:
    n: int
    doc_id: str
    title: str
    section: str


@dataclass
class ToolTrace:
    name: str
    arguments: dict[str, Any]
    output: str


@dataclass
class Answer:
    conversation_id: str
    text: str
    sources: list[Source] = field(default_factory=list)
    tool_calls: list[ToolTrace] = field(default_factory=list)
    blocked: bool = False
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0


def format_context(hits: list[Hit]) -> str:
    parts = [
        f"[{i}] {h.chunk.title} > {h.chunk.section} ({h.chunk.doc_id})\n{h.chunk.text}"
        for i, h in enumerate(hits, 1)
    ]
    return "Documentation context:\n\n" + "\n\n".join(parts) if parts else "No context found."


class Assistant:
    def __init__(
        self,
        settings: Settings,
        provider: LLMProvider,
        index: Index,
        toolbox: ToolBox | None = None,
        store: ConversationStore | None = None,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.index = index
        self.toolbox = toolbox
        self.store = store or ConversationStore()

    def retrieve(self, question: str) -> list[Hit]:
        cfg = self.settings.rag
        embedder = self.provider.embed if cfg.mode != "bm25" else None
        return self.index.search(question, k=cfg.top_k, mode=cfg.mode, embedder=embedder)

    async def ask(self, question: str, conversation_id: str | None = None) -> Answer:
        start = time.perf_counter()
        conv = self.store.get_or_create(conversation_id)
        verdict = check_question(question)
        if not verdict.allowed:
            log.warning("blocked question: %s", verdict.reason)
            return Answer(
                conv.id, f"Sorry, I can't process that request ({verdict.reason}).", blocked=True
            )

        hits = await asyncio.to_thread(self.retrieve, question)
        messages = [
            Message("system", self.settings.system_prompt),
            Message("system", format_context(hits)),
            *conv.messages,
            Message("user", question),
        ]
        tools = self.toolbox.tools if self.toolbox else None
        traces: list[ToolTrace] = []
        p_tok = c_tok = 0

        for _ in range(self.settings.mcp.max_tool_rounds + 1):
            resp = await asyncio.to_thread(self.provider.chat, messages, tools)
            p_tok += resp.prompt_tokens
            c_tok += resp.completion_tokens
            if not resp.tool_calls or self.toolbox is None:
                break
            messages.append(Message("assistant", resp.content, tool_calls=resp.tool_calls))
            for call in resp.tool_calls:
                bad = find_placeholder_args(call.arguments)
                if bad:
                    output = (
                        f"error: argument(s) {bad} look like placeholders. "
                        "Do not guess; ask the user for the real value."
                    )
                else:
                    output = await self.toolbox.call(call.name, call.arguments)
                log.info("tool %s(%s) -> %d chars", call.name, call.arguments, len(output))
                traces.append(ToolTrace(call.name, call.arguments, output))
                messages.append(Message("tool", output, tool_call_id=call.id, name=call.name))
        else:
            # Ran out of tool rounds: ask for a final answer without tools.
            resp = await asyncio.to_thread(self.provider.chat, messages, None)

        text = redact_secrets(resp.content.strip()) or "I could not produce an answer."
        self.store.append(conv, question, text)
        sources = [
            Source(i, h.chunk.doc_id, h.chunk.title, h.chunk.section) for i, h in enumerate(hits, 1)
        ]
        return Answer(
            conv.id,
            text,
            sources,
            traces,
            latency_ms=(time.perf_counter() - start) * 1000,
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
        )
