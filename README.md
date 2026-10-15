# OpsLens

**A small, pluggable framework for building RAG + MCP powered conversational assistants for
Linux and Kubernetes operations.**

Ask *"Why is my pod in CrashLoopBackOff?"* or *"Is my disk full?"* and OpsLens:

1. **checks the question** with guardrails (prompt-injection heuristics, length limits),
2. **retrieves** the most relevant documentation using **hybrid search** (BM25 + embeddings,
   fused with Reciprocal Rank Fusion),
3. lets the LLM **call read-only diagnostic tools** (`df`, `free`, `systemctl status`,
   `journalctl`, `kubectl get/describe`) exposed through a **Model Context Protocol (MCP) server**,
4. returns an answer with **numbered source citations**, the tool calls it made, token usage and
   latency, with any secrets in logs or tool output **redacted**.

It runs fully locally and open source with [Ollama](https://ollama.com), and works with any
OpenAI-compatible backend (vLLM, OpenAI, Groq, ...) by changing one config value.

```mermaid
flowchart LR
    U[User / curl / CLI] -->|POST /v1/query| API[REST API<br/>Starlette + Uvicorn]
    API --> G[Guardrails<br/>injection check, redaction]
    G --> R[Retriever<br/>BM25 + dense, RRF]
    R --> IDX[(Index<br/>chunks + embeddings)]
    G --> A[Agent loop<br/>max N tool rounds]
    R --> A
    A <-->|chat + tool schemas| P[LLM provider<br/>Ollama / OpenAI-compatible]
    A <-->|MCP over stdio| M[MCP server<br/>read-only Linux/K8s tools]
    M --> OS[(df, free, ps,<br/>systemctl, journalctl, kubectl)]
    A --> C[Conversation store<br/>multi-turn history]
    API --> MET[/metrics, /healthz, /readyz/]
```

## Features

| Area | What is implemented |
|---|---|
| **LLM providers** | `LLMProvider` protocol, OpenAI-compatible client with retries/back-off, a deterministic fake provider for tests and CI |
| **RAG** | Markdown-aware chunking with overlap, Okapi **BM25 written from scratch**, dense retrieval with cosine similarity, **hybrid search via Reciprocal Rank Fusion** |
| **Tools (MCP)** | MCP server with 7 **read-only** tools; no shell, argument allowlists/regex validation, timeouts, output truncation; usable from any MCP client |
| **Agent** | Function-calling loop with a bounded number of tool rounds, grounded system prompt, source citations, multi-turn conversation memory |
| **Guardrails** | Prompt-injection heuristics, input limits, secret redaction (API keys, tokens, passwords, private keys) |
| **Evaluation** | Labelled question set + IR metrics (Recall@k, MRR, MAP@k); a **quality gate in CI** fails if retrieval regresses |
| **Ops** | REST API, Prometheus-style `/metrics`, Kubernetes liveness/readiness probes, UBI-based `Containerfile`, `compose.yaml`, Kubernetes manifest |
| **Quality** | 32 pytest tests, `ruff` lint + format, `mypy --strict`, GitHub Actions on Python 3.11-3.13 plus a Podman container build and smoke test |

## Quick start (local, free, open source)

```bash
# 1. Model server
ollama pull llama3.2:3b          # chat model with tool-calling support
ollama pull nomic-embed-text     # embedding model for hybrid search

# 2. Install
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 3. Build the index (chunks + embeddings) and try it
opslens ingest
opslens ask "My pod keeps restarting, what should I check?"
opslens ask "Is my root disk running out of space?"     # triggers the disk_usage MCP tool

# 4. Run the API
opslens serve --port 8080
curl -s localhost:8080/v1/query -H 'content-type: application/json' \
     -d '{"query": "How do I open port 8080 in the firewall on RHEL?"}' | jq
```

No Ollama? Use BM25 only: `OPSLENS_RAG_MODE=bm25 opslens ingest --no-embeddings`.
Use a hosted model: set `OPSLENS_LLM_BASE_URL`, `OPSLENS_LLM_MODEL` and `OPSLENS_LLM_API_KEY`.

### Containers

```bash
podman build -t opslens -f Containerfile .
podman compose up                  # OpsLens + Ollama
kubectl apply -f deploy/k8s/opslens.yaml
```

### Use the MCP server on its own

The tools server is a standard MCP server, so other MCP clients can use it too:

```bash
opslens mcp-server                 # speaks MCP over stdio
npx @modelcontextprotocol/inspector opslens mcp-server   # explore it interactively
```

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/query` | `{"query": str, "conversation_id"?: str}` → answer, sources, tool calls, tokens, latency |
| `GET` | `/v1/conversations/{id}` | conversation history |
| `GET` | `/v1/tools` | MCP tools available to the model (JSON schema) |
| `GET` | `/healthz`, `/readyz` | liveness / readiness |
| `GET` | `/metrics` | query, block, error, tool-call and token counters |

## Retrieval evaluation

`eval/questions.yaml` holds 37 questions written the way users phrase them (not copied from the
docs), each labelled with the documents that answer it. Run `opslens eval -k 3`:

| mode | n | R@1 | R@3 | MRR | MAP@3 |
|---|---|---|---|---|---|
| bm25 | 37 | 0.716 | 0.932 | 0.867 | 0.829 |
| hybrid | 37 | *run locally with Ollama* | | | |

The one BM25 miss, *"Allow httpd to talk to a database over the network"*, is a vocabulary
mismatch (the docs say "Apache" and "connect"), exactly the case dense embeddings help with. Hybrid
mode adds embeddings and fuses both rankings with RRF.

## Project layout

```
src/opslens/
  providers/   LLM backends (OpenAI-compatible, fake)       config.py     YAML + env settings
  rag/         chunker, BM25, hybrid index                  agent.py      RAG + tool-calling loop
  tools/       MCP server (tools) + MCP client bridge       guardrails.py injection + redaction
  eval/        IR metrics + evaluation runner               api.py / cli.py
data/docs/     knowledge base (Markdown)                    eval/         labelled questions
tests/         unit + integration tests                     deploy/k8s/   Kubernetes manifest
```

## Design decisions

* **Read-only tools by design.** An assistant that can change production systems needs approval
  flows; this one only observes. Commands run without a shell, and arguments are validated, so a
  prompt-injected model cannot run `rm -rf`.
* **OpenAI-compatible API as the integration point.** Ollama, vLLM and most hosted providers
  speak it, so one client covers local and cloud models.
* **Deterministic tests.** A fake provider and an in-process MCP server mean CI needs no GPU, no
  model and no network.
* **Measure retrieval, not just generation.** Most RAG failures are retrieval failures, so
  retrieval quality is tracked with standard IR metrics and enforced in CI.

## Roadmap

- [ ] Streaming responses (Server-Sent Events)
- [ ] Answer-quality evaluation (faithfulness to retrieved context) with an LLM judge
- [ ] Persistent conversation store (PostgreSQL)
- [ ] Re-ranking with a cross-encoder
- [ ] Authentication and per-user rate limiting

## License

Apache-2.0
