# ───────────────────────────────────────────────────────────────
#  HubSpot MCP + SuperGateway   (HTTP/SSE on port 8080)
# ───────────────────────────────────────────────────────────────

FROM python:3.10-slim-bookworm   # keep your chosen base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# copy code first so that requirements caching still works
COPY . /app

# install the package *plus* supergateway
RUN pip install --no-cache-dir . \
    && pip install --no-cache-dir mcp-supergateway==0.5.2

# download and cache the SBERT model (unchanged)
RUN mkdir -p /app/models && \
    python - <<'PY'
from sentence_transformers import SentenceTransformer
m = SentenceTransformer("all-MiniLM-L6-v2")
m.save("/app/models/all-MiniLM-L6-v2")
PY

# health-check path for Railway
EXPOSE 8080

# ------------- ENTRYPOINT -------------
# SuperGateway starts the stdio server and exposes HTTP/SSE
ENTRYPOINT ["/bin/sh", "-c", "\
  supergateway \
    --stdio-command 'mcp-server-hubspot --access-token $HUBSPOT_ACCESS_TOKEN' \
    --listen-host 0.0.0.0 \
    --listen-port ${PORT:-8080} \
"]