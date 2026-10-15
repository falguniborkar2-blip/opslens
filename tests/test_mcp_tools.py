import asyncio

from opslens.tools.mcp_client import ToolBox
from opslens.tools.mcp_server import server


def test_toolbox_lists_and_calls_tools() -> None:
    async def run() -> None:
        async with ToolBox(server) as tb:
            assert {"disk_usage", "memory_usage", "service_status", "kubectl_get"} <= tb.names
            schema = next(t for t in tb.tools if t["function"]["name"] == "disk_usage")
            assert schema["type"] == "function"
            assert "path" in schema["function"]["parameters"]["properties"]
            out = await tb.call("disk_usage", {"path": "/"})
            assert "Filesystem" in out or "not installed" in out
            assert (await tb.call("rm_rf", {})).startswith("error: unknown tool")

    asyncio.run(run())


def test_tools_validate_arguments() -> None:
    async def run() -> None:
        async with ToolBox(server) as tb:
            assert "invalid unit" in await tb.call("service_status", {"unit": "sshd; rm -rf /"})
            assert "must be one of" in await tb.call("kubectl_get", {"resource": "secrets"})
            assert "does not exist" in await tb.call("disk_usage", {"path": "/no/such/dir"})
            assert "sort_by" in await tb.call("top_processes", {"sort_by": "evil"})

    asyncio.run(run())
