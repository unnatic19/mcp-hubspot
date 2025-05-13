#!/usr/bin/env bash
set -e
: "${HUBSPOT_ACCESS_TOKEN:?Need to set HUBSPOT_ACCESS_TOKEN}"

exec supergateway \
     --stdio-command "mcp-server-hubspot --access-token $HUBSPOT_ACCESS_TOKEN" \
     --listen-host 0.0.0.0 --listen-port "${PORT:-8080}"
