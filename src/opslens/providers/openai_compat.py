"""Provider for any OpenAI-compatible endpoint (Ollama, vLLM, OpenAI, Groq, ...)."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from .base import ChatResponse, Message, ProviderError, ToolCall


def _to_wire(msg: Message) -> dict[str, Any]:
    out: dict[str, Any] = {"role": msg.role, "content": msg.content}
    if msg.tool_calls:
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
            for tc in msg.tool_calls
        ]
    if msg.tool_call_id:
        out["tool_call_id"] = msg.tool_call_id
    if msg.name:
        out["name"] = msg.name
    return out


def _parse_args(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderError(f"model returned invalid tool arguments: {raw!r}") from exc
    return parsed if isinstance(parsed, dict) else {}


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        embedding_model: str | None = None,
        temperature: float = 0.1,
        timeout_s: float = 120.0,
        max_retries: int = 2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), headers=headers, timeout=timeout_s, transport=transport
        )
        self.model = model
        self.embedding_model = embedding_model
        self.temperature = temperature
        self.max_retries = max_retries

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._client.post(path, json=payload)
                if resp.status_code >= 500 or resp.status_code == 429:
                    raise httpx.HTTPStatusError("retryable", request=resp.request, response=resp)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
                return data
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status is not None and status < 500 and status != 429:
                    break
                if attempt < self.max_retries:
                    time.sleep(0.5 * 2**attempt)
        raise ProviderError(f"LLM request to {path} failed: {last_exc}") from last_exc

    def chat(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [_to_wire(m) for m in messages],
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools
        data = self._post("/chat/completions", payload)
        try:
            choice = data["choices"][0]["message"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"unexpected response shape: {data!r}") from exc
        calls = [
            ToolCall(
                id=tc.get("id") or f"call_{i}",
                name=tc["function"]["name"],
                arguments=_parse_args(tc["function"].get("arguments")),
            )
            for i, tc in enumerate(choice.get("tool_calls") or [])
        ]
        usage = data.get("usage") or {}
        return ChatResponse(
            content=choice.get("content") or "",
            tool_calls=calls,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.embedding_model:
            raise ProviderError("no embedding_model configured")
        data = self._post("/embeddings", {"model": self.embedding_model, "input": texts})
        items = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
        return [list(map(float, item["embedding"])) for item in items]
