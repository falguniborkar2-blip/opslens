"""REST API (Starlette/ASGI) exposing the assistant.

Endpoints
  POST /v1/query                      {"query": "...", "conversation_id": "..."?}
  GET  /v1/conversations/{id}         conversation history
  GET  /v1/tools                      MCP tools the assistant can use
  GET  /healthz  /readyz              liveness / readiness probes (Kubernetes-friendly)
  GET  /metrics                       Prometheus text format
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import asdict
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from .agent import Assistant
from .config import Settings, load_settings
from .providers import ProviderError, build_provider
from .rag.index import Index
from .tools.mcp_client import ToolBox

log = logging.getLogger("opslens.api")


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, max_length=64)


class Metrics:
    def __init__(self) -> None:
        self.counters: dict[str, float] = {
            "opslens_queries_total": 0,
            "opslens_queries_blocked_total": 0,
            "opslens_errors_total": 0,
            "opslens_tool_calls_total": 0,
            "opslens_tokens_total": 0,
            "opslens_latency_ms_sum": 0.0,
        }

    def render(self) -> str:
        return "".join(f"{k} {v}\n" for k, v in self.counters.items())


def build_assistant(settings: Settings, toolbox: ToolBox | None) -> Assistant:
    if not settings.rag.index_path.exists():
        raise RuntimeError(f"index not found at {settings.rag.index_path}; run `opslens ingest`")
    return Assistant(
        settings, build_provider(settings.llm), Index.load(settings.rag.index_path), toolbox
    )


def create_app(assistant: Assistant | None = None, settings: Settings | None = None) -> Starlette:
    metrics = Metrics()

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            if assistant is not None:
                app.state.assistant = assistant
            else:
                cfg = settings or load_settings()
                toolbox = None
                if cfg.mcp.enabled:
                    toolbox = await stack.enter_async_context(
                        ToolBox.stdio(cfg.mcp.command, cfg.mcp.args)
                    )
                    log.info("MCP tools loaded: %s", sorted(toolbox.names))
                app.state.assistant = build_assistant(cfg, toolbox)
            yield

    async def query(request: Request) -> JSONResponse:
        try:
            body = QueryRequest.model_validate(await request.json())
        except (ValidationError, ValueError) as exc:
            detail: Any = exc.errors() if isinstance(exc, ValidationError) else "invalid JSON"
            return JSONResponse({"error": "bad_request", "detail": detail}, status_code=422)
        bot: Assistant = request.app.state.assistant
        metrics.counters["opslens_queries_total"] += 1
        try:
            ans = await bot.ask(body.query, body.conversation_id)
        except ProviderError as exc:
            metrics.counters["opslens_errors_total"] += 1
            log.error("provider error: %s", exc)
            return JSONResponse({"error": "llm_unavailable", "detail": str(exc)}, status_code=503)
        if ans.blocked:
            metrics.counters["opslens_queries_blocked_total"] += 1
        metrics.counters["opslens_tool_calls_total"] += len(ans.tool_calls)
        metrics.counters["opslens_tokens_total"] += ans.prompt_tokens + ans.completion_tokens
        metrics.counters["opslens_latency_ms_sum"] += ans.latency_ms
        return JSONResponse(asdict(ans))

    async def conversation(request: Request) -> JSONResponse:
        bot: Assistant = request.app.state.assistant
        conv = bot.store.get(request.path_params["conv_id"])
        if conv is None:
            return JSONResponse({"error": "not_found"}, status_code=404)
        return JSONResponse(
            {
                "conversation_id": conv.id,
                "messages": [{"role": m.role, "content": m.content} for m in conv.messages],
            }
        )

    async def tools(request: Request) -> JSONResponse:
        bot: Assistant = request.app.state.assistant
        return JSONResponse({"tools": bot.toolbox.tools if bot.toolbox else []})

    async def healthz(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def readyz(request: Request) -> JSONResponse:
        ready = getattr(request.app.state, "assistant", None) is not None
        return JSONResponse({"ready": ready}, status_code=200 if ready else 503)

    async def metrics_ep(request: Request) -> PlainTextResponse:
        return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")

    return Starlette(
        routes=[
            Route("/v1/query", query, methods=["POST"]),
            Route("/v1/conversations/{conv_id}", conversation),
            Route("/v1/tools", tools),
            Route("/healthz", healthz),
            Route("/readyz", readyz),
            Route("/metrics", metrics_ep),
        ],
        lifespan=lifespan,
    )
