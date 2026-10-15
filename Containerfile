# Red Hat Universal Base Image: freely redistributable, runs rootless as UID 1001.
FROM registry.access.redhat.com/ubi9/python-312:latest

LABEL org.opencontainers.image.title="opslens" \
      org.opencontainers.image.description="RAG + MCP assistant for Linux/Kubernetes ops" \
      org.opencontainers.image.licenses="Apache-2.0"

# procps-ng provides ps/free for the MCP diagnostics tools.
USER 0
RUN yum install -y --setopt=install_weak_deps=False procps-ng && yum clean all
USER 1001

WORKDIR /opt/app-root/src
COPY --chown=1001:0 pyproject.toml README.md LICENSE ./
COPY --chown=1001:0 src ./src
RUN pip install --no-cache-dir .

COPY --chown=1001:0 config.yaml ./
COPY --chown=1001:0 data/docs ./data/docs
COPY --chown=1001:0 eval ./eval

# Build a BM25 index at image build time so the container starts without an LLM.
# Run `opslens ingest` again at runtime for hybrid (embedding) search.
ENV OPSLENS_RAG_MODE=bm25
RUN opslens ingest --no-embeddings

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD curl -fs http://localhost:8080/healthz || exit 1
CMD ["opslens", "serve", "--host", "0.0.0.0", "--port", "8080"]
