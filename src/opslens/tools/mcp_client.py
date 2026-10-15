"""Bridge between MCP servers and the LLM's function-calling interface."""

from __future__ import annotations

import os
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import Client, StdioServerParameters

from ..guardrails import redact_secrets


class ToolBox:
    """Holds an open MCP session and exposes its tools in OpenAI function format.

    `server` can be `StdioServerParameters` (launch a subprocess), a URL (Streamable HTTP),
    or an in-process `MCPServer` instance (used in tests).
    """

    def __init__(self, server: Any) -> None:
        self._server = server
        self._stack = AsyncExitStack()
        self._client: Client | None = None
        self.tools: list[dict[str, Any]] = []
        self.names: set[str] = set()

    @classmethod
    def stdio(cls, command: str, args: list[str]) -> ToolBox:
        # "python" means "the interpreter running OpsLens", so the server sees the same venv.
        if command in {"python", "python3"}:
            command = sys.executable
        # The MCP SDK passes only a minimal environment to subprocesses; keep PATH (to find
        # df/systemctl/kubectl), PYTHONPATH and KUBECONFIG so tools behave like the shell.
        env = {
            k: v
            for k in ("PATH", "PYTHONPATH", "KUBECONFIG", "HOME", "LANG")
            if (v := os.environ.get(k)) is not None
        }
        return cls(StdioServerParameters(command=command, args=args, env=env))

    async def __aenter__(self) -> ToolBox:
        self._client = await self._stack.enter_async_context(Client(self._server))
        listed = await self._client.list_tools()
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.input_schema,
                },
            }
            for t in listed.tools
        ]
        self.names = {t.name for t in listed.tools}
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._stack.aclose()
        self._client = None

    async def call(self, name: str, arguments: dict[str, Any]) -> str:
        if self._client is None:
            raise RuntimeError("ToolBox is not connected")
        if name not in self.names:
            return f"error: unknown tool {name!r}"
        result = await self._client.call_tool(name, arguments)
        text = "\n".join(getattr(c, "text", "") for c in result.content).strip()
        prefix = "error: " if result.is_error and not text.startswith("error") else ""
        return redact_secrets(prefix + text)
