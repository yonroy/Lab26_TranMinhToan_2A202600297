# Lab: Build a Database MCP Server with FastMCP and SQLite

## Goal

Build a Model Context Protocol (MCP) server using FastMCP that exposes a small database through:

- `search`
- `insert`
- `aggregate`

You must also expose the database schema as an MCP resource, test the server with Inspector or equivalent tooling, and show the server working from at least one MCP client.

## Learning Outcomes

By the end of this lab, students should be able to:

- explain what MCP tools and resources are
- build a FastMCP server in Python
- connect FastMCP to a SQLite database
- safely validate database requests before executing SQL
- expose dynamic schema context through `@mcp.resource(...)`
- test tool schemas, normal calls, and error responses
- connect the server to an MCP client such as Claude Code, Codex, or Gemini CLI

## Required Features

### Part 1: MCP Server

Implement a FastMCP server that exposes exactly these tool categories:

1. `search`
2. `insert`
3. `aggregate`

Your server may use SQLite for the main implementation. If you want to support PostgreSQL too, design the code so the database layer can be swapped later.

### Part 2: Resource

Expose database schema information as MCP resources:

- one resource for the full database schema
- one dynamic resource template for a single table schema

Suggested URIs:

- `schema://database`
- `schema://table/{table_name}`

### Part 3: Validation and Error Handling

Your tools must reject unsafe or invalid requests:

- unknown table names
- unknown column names
- unsupported filter operators
- invalid aggregate requests
- empty inserts

Do not build SQL by blindly concatenating raw user input.

### Part 4: Testing and Verification

Verify all of the following:

1. the server starts correctly
2. the three tools are discoverable
3. the schema resource is discoverable
4. valid tool calls return useful results
5. invalid tool calls return clear errors
6. at least one MCP client can connect and use the server

### Part 5: Demo Deliverables

Prepare:

- GitHub repository
- setup instructions
- tool descriptions
- testing steps
- at least one client configuration example
- short demo video, around 2 minutes

Inspector screenshots are recommended if you use MCP Inspector.

## Suggested Project Structure

```text
implementation/
  db.py
  init_db.py
  mcp_server.py
  verify_server.py
  tests/
    test_server.py
```

## Recommended Data Model

Use a small relational dataset so `search`, `insert`, and `aggregate` are easy to demo. Example:

- `students`
- `courses`
- `enrollments`

## Example Tasks to Demonstrate

- search all students in cohort `A1`
- insert a new student
- count rows in a table
- compute average score by cohort
- read the full schema resource
- read `schema://table/students`
- show an invalid request, such as searching a missing table

## FastMCP and Inspector References

- FastMCP quickstart: https://gofastmcp.com/v2/getting-started/quickstart
- FastMCP resources: https://gofastmcp.com/v2/servers/resources
- MCP Inspector: https://modelcontextprotocol.io/docs/tools/inspector

## Client Setup Notes

### Claude Code

Anthropic documents local JSON config and `claude mcp add` flows here:

- https://code.claude.com/docs/en/mcp

Claude Code supports MCP resources via `@server:resource-uri` references and supports environment variable expansion in `.mcp.json`.

### Codex

OpenAI documents Codex MCP setup here:

- https://developers.openai.com/learn/docs-mcp

Codex supports MCP server configuration through the CLI and `~/.codex/config.toml`.

### Gemini CLI

Gemini CLI has a built-in MCP manager. In the verified local workflow, the simplest path is:

```bash
gemini mcp add sqlite-lab /ABSOLUTE/PATH/TO/python /ABSOLUTE/PATH/TO/implementation/mcp_server.py --description "SQLite lab FastMCP server" --timeout 10000
gemini mcp list
```

Gemini CLI also documents configuration details here:

- https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md

Expected outcome:

- the server appears as `Connected`
- Gemini can discover `search`, `insert`, and `aggregate`
- a headless smoke test works with `gemini --allowed-mcp-server-names sqlite-lab --yolo -p "..."`

### Antigravity

Antigravity commonly uses an `mcp_config.json` file with a shape similar to Gemini CLI. Verify the current product behavior in your installed version before grading against exact UI steps.

## Deliverable Checklist

- working FastMCP server
- SQLite database and seed data
- `search`, `insert`, `aggregate` tools
- schema resource and schema resource template
- verification steps
- automated tests or repeatable verification script
- client configuration example
- README with setup and demo steps
- Inspector startup command or helper script
- at least one verified Gemini CLI or Claude/Codex client test

## Bonus

Optional bonus:

- add authentication for SSE or HTTP transport
- support both SQLite and PostgreSQL with the same MCP surface
- add richer output annotations or pagination

---

# Reference Implementation (this repo)

This repo ships a working solution under `implementation/`, packaged for Docker
and tested with MCP Inspector over HTTP transport.

## Layout

```
implementation/
  db.py                # SQLiteAdapter + ValidationError
  init_db.py           # schema + seed + create_database()
  mcp_server.py        # FastMCP app: 3 tools + 2 resources
  verify_server.py     # end-to-end smoke test over HTTP
  requirements.txt
  Dockerfile
  tests/test_db.py     # 12 adapter unit tests
docker-compose.yml
start_inspector.sh / start_inspector.ps1
plan.md
```

## Tools and resources

| Surface                          | Kind             | Notes                                                 |
| -------------------------------- | ---------------- | ----------------------------------------------------- |
| `search`                         | tool             | filters, projection, ORDER BY, LIMIT≤200, OFFSET      |
| `insert`                         | tool             | parameterized; rejects empty values / unknown columns |
| `aggregate`                      | tool             | `count`, `avg`, `sum`, `min`, `max`, optional GROUP BY |
| `schema://database`              | resource         | JSON snapshot of every table                          |
| `schema://table/{table_name}`    | resource template| JSON schema of one table                              |

Operators allowed in `filters[*].op`: `=`, `!=`, `<`, `<=`, `>`, `>=`, `LIKE`, `IN`.
Non-`count` metrics require a numeric column.

## Run with Docker

```bash
docker compose up --build
# server now listening on http://localhost:8000/mcp
```

The database file lives in `./implementation/data/students.db` (created on
first boot, idempotent thereafter).

## Demo with MCP Inspector

In a second terminal:

```bash
# macOS / Linux
./start_inspector.sh

# Windows PowerShell
./start_inspector.ps1
```

In the Inspector UI:

1. Transport Type = **Streamable HTTP**
2. URL = `http://localhost:8000/mcp`
3. Click **Connect**

Then exercise the surface:

- **Tools tab** — verify `search`, `insert`, `aggregate` appear with schemas.
- `search` → `{"table":"students","filters":[{"column":"cohort","op":"=","value":"A1"}],"order_by":"score","descending":true}`
- `insert` → `{"table":"students","values":{"name":"Demo","cohort":"A1","score":9.0}}`
- `aggregate` → `{"table":"students","metric":"avg","column":"score","group_by":"cohort"}`
- **Resources tab** — read `schema://database` and `schema://table/students`.
- **Error case** — call `search` with `{"table":"hackers"}` → returns
  `{"error":"unknown table: 'hackers'", "kind":"ValidationError"}`.

## Verify end-to-end

```bash
python implementation/verify_server.py --url http://localhost:8000/mcp
```

All checks should report `[PASS]`.

## Run adapter tests

```bash
pip install -r implementation/requirements.txt
pytest implementation/tests -q
```

## Client config (Claude Code, HTTP)

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

For stdio clients, set `MCP_TRANSPORT=stdio` and follow the patterns in
`Tips.md`.
