#!/usr/bin/env bash
set -euo pipefail               # fail fast

: "${HUBSPOT_ACCESS_TOKEN:?Need to set HUBSPOT_ACCESS_TOKEN}"

exec supergateway \
  --stdio "npx -y @hubspot/mcp-server --access-token ${HUBSPOT_ACCESS_TOKEN}" \
  --port 8080 \
  --outputTransport sse