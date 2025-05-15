#!/usr/bin/env bash
set -e

: "${HUBSPOT_ACCESS_TOKEN:?Need to set HUBSPOT_ACCESS_TOKEN}"

exec supergateway \
  --stdio "mcp-server-hubspot --access-token $HUBSPOT_ACCESS_TOKEN" \
  --port 8080 \
  --outputTransport sse          # optional; defaults to sse when --stdio is used