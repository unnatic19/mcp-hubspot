# ───────────────────────── base layer ─────────────────────────
FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ─── Python deps ──────────────────────────────────────────────
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .

# (optional) warm-cache the SBERT model so first start-up is fast
RUN python - <<'PY'
from sentence_transformers import SentenceTransformer
SentenceTransformer("all-MiniLM-L6-v2").save("/app/models")
PY

# ─── Node + SuperGateway ──────────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends nodejs npm && \
    npm install -g supergateway@2.7.0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ─── wrapper script & metadata ────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]