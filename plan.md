# Plan: FastMCP SQLite Server trên Docker, demo qua MCP Inspector

## Context

Lab26 yêu cầu xây dựng một FastMCP server expose 3 tools (`search`, `insert`, `aggregate`) và 2 resources schema (`schema://database`, `schema://table/{table_name}`) trên SQLite. Repo ban đầu chỉ có pseudocode trong `pseudocode/`.

Yêu cầu bổ sung:
- Server đóng gói trong **Docker** (Inspector kết nối qua **HTTP transport**, port 8000).
- Dataset: **students / courses / enrollments**.
- Kèm `docker-compose.yml` + script `start_inspector` cho cả Linux/macOS và Windows PowerShell.

Mục tiêu cuối: `docker compose up` → mở Inspector → thấy 3 tools + 2 resources, gọi thử thành công cả case hợp lệ và lỗi, đáp ứng đủ Rubric.

## Cấu trúc thư mục

```
implementation/
  db.py                  # SQLiteAdapter
  init_db.py             # SCHEMA_SQL + SEED_SQL + create_database()
  mcp_server.py          # FastMCP app: 3 tools + 2 resources
  verify_server.py       # smoke test qua HTTP
  requirements.txt       # fastmcp, httpx, pytest
  Dockerfile
  tests/
    test_db.py           # pytest cho adapter
docker-compose.yml
start_inspector.sh
start_inspector.ps1
README.md                # cập nhật setup/demo/client config
plan.md                  # file này
pseudocode/              # giữ nguyên
```

## Chi tiết triển khai

### 1. `implementation/init_db.py`
- 3 bảng: `students(id, name, cohort, score)`, `courses(id, code UNIQUE, title, credits)`, `enrollments(id, student_id, course_id, grade)`.
- Seed: 6–8 students cohort A1/A2/B1, 4 courses, ~10 enrollments.
- `create_database(path)`: idempotent.

### 2. `implementation/db.py`
`SQLiteAdapter` với:
- `connect()` mở connection mới, `row_factory = sqlite3.Row`.
- `list_tables()`, `get_table_schema(table)`.
- Validation: `_assert_table`, `_assert_columns`, `ALLOWED_OPERATORS`, `ALLOWED_METRICS`.
- `search(table, columns, filters, limit, offset, order_by, descending)` — parameterized.
- `insert(table, values)` — reject empty, parameterized.
- `aggregate(table, metric, column, filters, group_by)` — count/avg/sum/min/max.
- Raises `ValidationError` cho input không hợp lệ.

### 3. `implementation/mcp_server.py`
- Khởi tạo `FastMCP("SQLite Lab")`, adapter từ `DB_PATH`.
- 3 tool functions với docstrings + type hints.
- Bắt `ValidationError` → return `{"error": ...}`.
- Resources `schema://database` và `schema://table/{table_name}`.
- Entry point chọn transport theo `MCP_TRANSPORT` (`http` default, hoặc `stdio`).

### 4. `implementation/Dockerfile`
- `python:3.12-slim`, cài requirements, expose 8000, `CMD python mcp_server.py`.

### 5. `docker-compose.yml`
- Service `mcp` build `./implementation`, ports `8000:8000`, volume `./implementation/data:/data`.

### 6. Inspector scripts
- `start_inspector.sh` / `start_inspector.ps1`: chạy `npx -y @modelcontextprotocol/inspector`, hướng dẫn dán URL `http://localhost:8000/mcp` (transport Streamable HTTP).

### 7. `verify_server.py`
- Gọi list tools / `search` / `insert` / `aggregate` / read resource / case lỗi qua HTTP, in PASS/FAIL.

### 8. `tests/test_db.py`
- Pytest cho validation + happy path adapter.

### 9. README.md
- Setup, run Docker, run Inspector, demo checklist, client config (`.mcp.json` HTTP), run tests.

## Verification

1. `docker compose up --build` → server log "running on 0.0.0.0:8000".
2. `python implementation/verify_server.py` → tất cả PASS.
3. `start_inspector` → Inspector UI → connect → thấy 3 tools + 2 resources.
4. Demo gọi tool valid + invalid trong Inspector, chụp screenshot.
5. `pytest implementation/tests -q` → PASS.

## Out of scope (bonus)

- Auth HTTP, PostgreSQL adapter, pagination cursor.
