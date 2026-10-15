.PHONY: install lint test eval ingest serve image

install:   ## install in editable mode with dev tools
	pip install -e ".[dev]"
lint:      ## ruff + mypy
	ruff check src tests && ruff format --check src tests && mypy src
test:      ## run the test suite
	pytest -q
ingest:    ## build the search index (with embeddings if rag.mode != bm25)
	opslens ingest
eval:      ## retrieval metrics
	opslens eval -k 3 --show-failures
serve:     ## run the API on :8080
	opslens serve --port 8080
image:     ## build the container image
	podman build -t opslens -f Containerfile .
