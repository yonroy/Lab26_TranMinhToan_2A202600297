#!/usr/bin/env bash
# Launch MCP Inspector pointing at the dockerized FastMCP server.
# Prereq: `docker compose up` is running and exposing http://localhost:8000/mcp.

set -euo pipefail

URL="${MCP_URL:-http://localhost:8000/mcp}"

mkdir -p .npm-cache
export NPM_CONFIG_CACHE="$PWD/.npm-cache"

cat <<EOF
Starting MCP Inspector.

After the UI opens:
  1. Transport Type   = Streamable HTTP
  2. URL              = ${URL}
  3. Click "Connect"

You should then see:
  - tools:     search, insert, aggregate
  - resources: schema://database
  - templates: schema://table/{table_name}
EOF

exec npx -y @modelcontextprotocol/inspector
