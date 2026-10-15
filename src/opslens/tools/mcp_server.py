"""OpsLens MCP server: safe, READ-ONLY Linux and Kubernetes diagnostics tools.

Run standalone (any MCP client can use it, e.g. Claude Desktop or the MCP Inspector):

    python -m opslens.tools.mcp_server

Security model:
* Every tool is read-only; nothing here can change system state.
* Commands are executed without a shell (no injection via arguments).
* Arguments are validated against strict allowlists / regexes.
* Output is truncated and secrets are redacted before reaching the LLM.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from ..guardrails import redact_secrets

MAX_OUTPUT = 4000
TIMEOUT_S = 10

_UNIT = re.compile(r"^[A-Za-z0-9@_.:\-]{1,128}$")
_K8S_NAME = re.compile(r"^[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?$")
K8S_RESOURCES = frozenset(
    {
        "pods",
        "deployments",
        "services",
        "nodes",
        "events",
        "replicasets",
        "jobs",
        "statefulsets",
        "daemonsets",
        "configmaps",
        "persistentvolumeclaims",
        "namespaces",
    }
)

server = MCPServer(
    "opslens-linux-tools",
    instructions="Read-only diagnostics for Linux hosts and Kubernetes clusters.",
)


def _run(cmd: list[str]) -> str:
    if shutil.which(cmd[0]) is None:
        return f"error: '{cmd[0]}' is not installed on this host"
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S, check=False)
    except subprocess.TimeoutExpired:
        return f"error: command timed out after {TIMEOUT_S}s"
    out = (proc.stdout or "") + (f"\n[stderr]\n{proc.stderr}" if proc.stderr.strip() else "")
    out = redact_secrets(out.strip())
    if len(out) > MAX_OUTPUT:
        out = out[:MAX_OUTPUT] + f"\n... [truncated {len(out) - MAX_OUTPUT} chars]"
    return out or "(no output)"


@server.tool()
def disk_usage(path: str = "/") -> str:
    """Show filesystem disk usage (df -h) for the filesystem containing `path`."""
    if not Path(path).exists():
        return f"error: path {path!r} does not exist"
    return _run(["df", "-h", "--", path])


@server.tool()
def memory_usage() -> str:
    """Show RAM and swap usage (free -h)."""
    return _run(["free", "-h"])


@server.tool()
def top_processes(limit: int = 10, sort_by: str = "cpu") -> str:
    """List the top processes by 'cpu' or 'mem' usage."""
    if sort_by not in {"cpu", "mem"}:
        return "error: sort_by must be 'cpu' or 'mem'"
    limit = max(1, min(int(limit), 50))
    out = _run(["ps", "-eo", "pid,user,%cpu,%mem,comm", f"--sort=-%{sort_by}"])
    return "\n".join(out.splitlines()[: limit + 1])


@server.tool()
def service_status(unit: str) -> str:
    """Show `systemctl status` for a systemd unit, e.g. 'sshd' or 'nginx.service'."""
    if not _UNIT.match(unit):
        return "error: invalid unit name"
    return _run(["systemctl", "status", "--no-pager", "--lines=0", "--", unit])


@server.tool()
def journal_tail(unit: str, lines: int = 30) -> str:
    """Show the last log lines for a systemd unit from the journal."""
    if not _UNIT.match(unit):
        return "error: invalid unit name"
    lines = max(1, min(int(lines), 200))
    return _run(["journalctl", "--no-pager", "-u", unit, "-n", str(lines)])


@server.tool()
def kubectl_get(resource: str, namespace: str = "default", name: str = "") -> str:
    """Read-only `kubectl get` for common resources (pods, deployments, events, ...)."""
    resource = resource.lower()
    if resource not in K8S_RESOURCES:
        return f"error: resource must be one of {sorted(K8S_RESOURCES)}"
    if not _K8S_NAME.match(namespace) or (name and not _K8S_NAME.match(name)):
        return "error: invalid namespace or resource name"
    cmd = ["kubectl", "get", resource, "-n", namespace, "-o", "wide"]
    if name:
        cmd.insert(3, name)
    return _run(cmd)


@server.tool()
def kubectl_describe_pod(name: str, namespace: str = "default") -> str:
    """`kubectl describe pod` - shows events such as CrashLoopBackOff or ImagePullBackOff."""
    if not _K8S_NAME.match(name) or not _K8S_NAME.match(namespace):
        return "error: invalid pod or namespace name"
    return _run(["kubectl", "describe", "pod", name, "-n", namespace])


def main() -> None:
    server.run()  # stdio transport


if __name__ == "__main__":
    main()
