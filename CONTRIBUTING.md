# Contributing

1. Fork and create a branch: `git checkout -b feature/my-change`.
2. `make install`, then make your change with tests.
3. `make lint test` must pass (CI runs the same checks on Python 3.11-3.13).
4. If you change retrieval or the docs corpus, run `make eval` and include the before/after
   table in your PR description.
5. New MCP tools must be **read-only**, validate their arguments, and run without a shell.

Adding an LLM backend: implement the `LLMProvider` protocol in `src/opslens/providers/`
(`chat()` and `embed()`) and register it in `build_provider()`.
