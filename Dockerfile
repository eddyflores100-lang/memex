# Memex Dockerfile — runs the memex MCP stdio server by default.
# Build: docker build -t memex:0.3.0rc1 .
# Run:   docker run -i memex:0.3.0rc1
#
# Default entrypoint: the MCP stdio server (`memex mcp serve`). Registry
# inspectors build this image and speak MCP `initialize` /
# `tools/list` over stdio with no daemon and no Ollama required.
#
# To run the HTTP memory server instead (needs a reachable Ollama for
# embeddings — see docker-compose.yml or point OLLAMA_URL at your host):
#   docker run -p 19420:19420 -v memex-data:/data \
#     -e MEMEX_ENTRYPOINT=http memex:0.3.0rc1

FROM python:3.12-slim

LABEL org.opencontainers.image.title="memex"
LABEL org.opencontainers.image.description="Local-first, zero-LLM agent memory"
LABEL org.opencontainers.image.source="https://github.com/eddyflores100-lang/memex"
LABEL org.opencontainers.image.licenses="AliceLabs Proprietary v1.0"
LABEL org.opencontainers.image.version="0.3.0rc1"

# System deps for chromadb + sqlite
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install memex from source
COPY pyproject.toml README.md LICENSE-ALICELABS.txt ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# Persist memory store outside the container. MEMEX_* env names are
# canonical post-rename; the legacy COGITO_* spellings are still honored
# by config._ENV_MAP for pre-rename deployments.
VOLUME ["/data"]
ENV MEMEX_STORE_PATH=/data/store
ENV MEMEX_QUEUE_DIR=/data/queue
ENV MEM0_TELEMETRY=False
ENV ANONYMIZED_TELEMETRY=False
ENV CHROMA_TELEMETRY_DISABLED=True
ENV MEMEX_PORT=19420

# Default Ollama URL points at host (override via env)
ENV MEMEX_OLLAMA_URL=http://host.docker.internal:11434

# Which server to run: "mcp" (default, stdio, no Ollama needed) or "http"
ENV MEMEX_ENTRYPOINT=mcp

EXPOSE 19420

# Health check: GET /health. Only meaningful for MEMEX_ENTRYPOINT=http;
# under the default mcp entrypoint there is no HTTP surface, so this simply
# reports unhealthy and callers running mcp mode should ignore/override it.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD if [ "$MEMEX_ENTRYPOINT" = "http" ]; then curl -fs "http://localhost:${MEMEX_PORT}/health" || exit 1; else exit 0; fi

CMD ["sh", "-c", "if [ \"$MEMEX_ENTRYPOINT\" = \"http\" ]; then exec memex-server --host 0.0.0.0; else exec memex mcp serve; fi"]
