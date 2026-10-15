import json

import httpx
import pytest

from opslens.providers import Message, OpenAICompatibleProvider, ProviderError


def _provider(handler):  # type: ignore[no-untyped-def]
    return OpenAICompatibleProvider(
        "http://llm/v1",
        "m",
        api_key="k",
        embedding_model="e",
        transport=httpx.MockTransport(handler),
        max_retries=2,
    )


def test_chat_parses_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(req.content)
        seen["auth"] = req.headers["authorization"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "c1",
                                    "function": {
                                        "name": "disk_usage",
                                        "arguments": '{"path": "/"}',
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            },
        )

    resp = _provider(handler).chat([Message("user", "hi")], tools=[{"type": "function"}])
    assert resp.tool_calls[0].name == "disk_usage"
    assert resp.tool_calls[0].arguments == {"path": "/"}
    assert resp.prompt_tokens == 10
    assert seen["auth"] == "Bearer k"
    assert seen["body"]["tools"] == [{"type": "function"}]


def test_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("time.sleep", lambda s: None)
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    assert _provider(handler).chat([Message("user", "hi")]).content == "ok"
    assert calls["n"] == 3


def test_client_error_not_retried() -> None:
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401, json={"error": "bad key"})

    with pytest.raises(ProviderError):
        _provider(handler).chat([Message("user", "hi")])
    assert calls["n"] == 1


def test_embeddings_sorted_by_index() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            },
        )

    assert _provider(handler).embed(["a", "b"]) == [[1.0, 0.0], [0.0, 1.0]]
