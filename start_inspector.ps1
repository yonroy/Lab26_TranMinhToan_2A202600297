#!/usr/bin/env pwsh
# Launch MCP Inspector pointing at the dockerized FastMCP server.
# Prereq: `docker compose up` is running and exposing http://localhost:8000/mcp.

$ErrorActionPreference = "Stop"

$Url = if ($env:MCP_URL) { $env:MCP_URL } else { "http://localhost:8000/mcp" }

New-Item -ItemType Directory -Force -Path ".npm-cache" | Out-Null
$env:NPM_CONFIG_CACHE = (Resolve-Path ".npm-cache").Path

Write-Host ""
Write-Host "Starting MCP Inspector."
Write-Host ""
Write-Host "After the UI opens:"
Write-Host "  1. Transport Type   = Streamable HTTP"
Write-Host "  2. URL              = $Url"
Write-Host "  3. Click 'Connect'"
Write-Host ""
Write-Host "You should then see:"
Write-Host "  - tools:     search, insert, aggregate"
Write-Host "  - resources: schema://database"
Write-Host "  - templates: schema://table/{table_name}"
Write-Host ""

npx -y "@modelcontextprotocol/inspector"
