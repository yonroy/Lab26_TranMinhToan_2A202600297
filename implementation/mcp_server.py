"""FastMCP server exposing search/insert/aggregate over SQLite + schema resources."""

from __future__ import annotations

import json
import os
from typing import Any

from fastmcp import FastMCP

from db import SQLiteAdapter, ValidationError
from init_db import create_database

DB_PATH = create_database(os.environ.get("DB_PATH"))
adapter = SQLiteAdapter(DB_PATH)

mcp = FastMCP("SQLite Lab MCP Server")


@mcp.tool(name="search")
def search(
    table: str,
    filters: list[dict] | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search rows in a table with optional filters, projection, ordering, and pagination.

    Args:
        table: Table name (must exist in the database).
        filters: List of {"column", "op", "value"}. Operators: =, !=, <, <=, >, >=, LIKE, IN.
        columns: Optional projection; default selects all columns.
        limit: Max rows returned (1..200, default 20).
        offset: Rows to skip (default 0).
        order_by: Column to order by; must be a real column.
        descending: Whether to sort DESC (default False).

    Returns:
        {"table", "count", "limit", "offset", "rows"} on success
        or {"error", "kind"} on validation failure.
    """
    try:
        return adapter.search(
            table=table,
            columns=columns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
        )
    except ValidationError as e:
        return {"error": str(e), "kind": "ValidationError"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "kind": "ServerError"}


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert a single row into a table.

    Args:
        table: Target table.
        values: Non-empty {column: value} object; every column must exist in the table.

    Returns:
        {"table", "id", "values"} on success or {"error", "kind"} on validation failure.
    """
    try:
        return adapter.insert(table=table, values=values)
    except ValidationError as e:
        return {"error": str(e), "kind": "ValidationError"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "kind": "ServerError"}


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: list[dict] | None = None,
    group_by: str | None = None,
) -> dict[str, Any]:
    """Aggregate rows with count / avg / sum / min / max, optionally grouped.

    Args:
        table: Table to aggregate.
        metric: One of count, avg, sum, min, max.
        column: Required for non-count metrics; must be numeric.
        filters: Same shape as `search` filters.
        group_by: Optional grouping column.

    Returns:
        {"table", "metric", "column", "group_by", "rows":[{group_value?, value}]}
        or {"error", "kind"}.
    """
    try:
        return adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by,
        )
    except ValidationError as e:
        return {"error": str(e), "kind": "ValidationError"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "kind": "ServerError"}


@mcp.resource("schema://database")
def database_schema() -> str:
    """Full database schema as JSON: {table: [{name,type,notnull,pk,default}, ...]}."""
    return json.dumps(adapter.database_schema(), indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Schema for a single table, as JSON."""
    try:
        return json.dumps(
            {table_name: adapter.get_table_schema(table_name)}, indent=2
        )
    except ValidationError as e:
        return json.dumps({"error": str(e), "kind": "ValidationError"})


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "http").lower()
    if transport == "stdio":
        mcp.run()
        return
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    main()
