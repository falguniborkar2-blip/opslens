"""Command-line interface: `opslens ingest | ask | serve | eval | mcp-server`."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from .config import Settings, load_settings
from .providers import build_provider


def cmd_ingest(cfg: Settings, args: argparse.Namespace) -> int:
    from .rag import Index, load_corpus

    chunks = load_corpus(cfg.rag.docs_dir, cfg.rag.chunk_size, cfg.rag.chunk_overlap)
    embedder = None
    if cfg.rag.mode != "bm25" and not args.no_embeddings:
        embedder = build_provider(cfg.llm).embed
    index = Index.build(chunks, embedder)
    index.save(cfg.rag.index_path)
    docs = len({c.doc_id for c in chunks})
    print(
        f"indexed {len(chunks)} chunks from {docs} documents -> {cfg.rag.index_path}"
        f" (embeddings: {'yes' if embedder else 'no'})"
    )
    return 0


async def _ask(cfg: Settings, question: str, as_json: bool) -> int:
    from .api import build_assistant
    from .tools.mcp_client import ToolBox

    async def run(toolbox: ToolBox | None) -> int:
        ans = await build_assistant(cfg, toolbox).ask(question)
        if as_json:
            print(json.dumps(asdict(ans), indent=2))
            return 0
        print(ans.text, "\n")
        for t in ans.tool_calls:
            print(f"  tool: {t.name}({json.dumps(t.arguments)})")
        for s in ans.sources:
            print(f"  [{s.n}] {s.title} > {s.section}")
        return 0

    if cfg.mcp.enabled:
        async with ToolBox.stdio(cfg.mcp.command, cfg.mcp.args) as tb:
            return await run(tb)
    return await run(None)


def cmd_eval(cfg: Settings, args: argparse.Namespace) -> int:
    from .eval.runner import evaluate, load_questions
    from .rag import Index

    index = Index.load(cfg.rag.index_path)
    questions = load_questions(Path(args.questions))
    modes = ["bm25"] + (["dense", "hybrid"] if index.embeddings is not None else [])
    embedder = build_provider(cfg.llm).embed if index.embeddings is not None else None
    print(f"| mode   |   n |  R@1  |  R@{args.k}  |  MRR  | MAP@{args.k} |")
    print("|--------|-----|-------|-------|-------|-------|")
    worst = None
    for mode in modes:
        res = evaluate(index, questions, mode, args.k, embedder)  # type: ignore[arg-type]
        print(res.row())
        worst = worst or res
    if args.show_failures and worst:
        print("\nmisses (bm25):", *worst.failures, sep="\n  - ")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opslens", description=__doc__)
    parser.add_argument("-c", "--config", default=None, help="path to config.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ingest", help="chunk documents and build the search index")
    p.add_argument("--no-embeddings", action="store_true", help="BM25 only, no LLM needed")
    p = sub.add_parser("ask", help="ask a single question")
    p.add_argument("question")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("serve", help="run the REST API")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    p = sub.add_parser("eval", help="evaluate retrieval quality")
    p.add_argument("--questions", default="eval/questions.yaml")
    p.add_argument("-k", type=int, default=3)
    p.add_argument("--show-failures", action="store_true")
    sub.add_parser("mcp-server", help="run the read-only MCP tools server on stdio")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.cmd == "mcp-server":
        from .tools.mcp_server import main as mcp_main

        mcp_main()
        return 0
    cfg = load_settings(args.config)
    if args.cmd == "ingest":
        return cmd_ingest(cfg, args)
    if args.cmd == "ask":
        return asyncio.run(_ask(cfg, args.question, args.json))
    if args.cmd == "eval":
        return cmd_eval(cfg, args)
    if args.cmd == "serve":
        import uvicorn

        from .api import create_app

        uvicorn.run(create_app(settings=cfg), host=args.host, port=args.port)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
