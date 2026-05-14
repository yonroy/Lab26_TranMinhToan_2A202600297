"""SQLite adapter with strict identifier and operator validation."""

from __future__ import annotations

import sqlite3
from typing import Any, Iterable


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


ALLOWED_OPERATORS = {"=", "!=", "<", "<=", ">", ">=", "LIKE", "IN"}
ALLOWED_METRICS = {"count", "avg", "sum", "min", "max"}
NUMERIC_AFFINITIES = {"INTEGER", "REAL", "NUMERIC", "DOUBLE", "FLOAT"}
MAX_LIMIT = 200


class SQLiteAdapter:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ------------------------------------------------------------------ introspection

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            ).fetchall()
        return [r["name"] for r in rows]

    def get_table_schema(self, table: str) -> list[dict[str, Any]]:
        self._assert_table(table)
        with self.connect() as conn:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [
            {
                "name": r["name"],
                "type": r["type"],
                "notnull": bool(r["notnull"]),
                "pk": bool(r["pk"]),
                "default": r["dflt_value"],
            }
            for r in rows
        ]

    def database_schema(self) -> dict[str, list[dict[str, Any]]]:
        return {t: self.get_table_schema(t) for t in self.list_tables()}

    # ------------------------------------------------------------------ validation

    def _assert_table(self, table: str) -> None:
        if not isinstance(table, str) or not table:
            raise ValidationError("table must be a non-empty string")
        if table not in self.list_tables():
            raise ValidationError(f"unknown table: {table!r}")

    def _column_names(self, table: str) -> set[str]:
        return {c["name"] for c in self.get_table_schema(table)}

    def _assert_columns(self, table: str, cols: Iterable[str]) -> None:
        known = self._column_names(table)
        for c in cols:
            if c not in known:
                raise ValidationError(f"unknown column {c!r} for table {table!r}")

    # ------------------------------------------------------------------ helpers

    def _build_where(self, table: str, filters: list[dict] | None) -> tuple[str, list]:
        if not filters:
            return "", []
        if not isinstance(filters, list):
            raise ValidationError("filters must be a list of {column, op, value}")

        known_cols = self._column_names(table)
        clauses: list[str] = []
        params: list = []
        for f in filters:
            if not isinstance(f, dict):
                raise ValidationError("each filter must be an object")
            col = f.get("column")
            op = (f.get("op") or "=").upper()
            val = f.get("value")
            if col not in known_cols:
                raise ValidationError(f"unknown column {col!r} for table {table!r}")
            if op not in ALLOWED_OPERATORS:
                raise ValidationError(
                    f"unsupported operator {op!r}; allowed: {sorted(ALLOWED_OPERATORS)}"
                )
            if op == "IN":
                if not isinstance(val, (list, tuple)) or not val:
                    raise ValidationError("IN requires a non-empty list value")
                placeholders = ",".join(["?"] * len(val))
                clauses.append(f"{col} IN ({placeholders})")
                params.extend(val)
            else:
                clauses.append(f"{col} {op} ?")
                params.append(val)
        return " WHERE " + " AND ".join(clauses), params

    # ------------------------------------------------------------------ tools

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: list[dict] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict:
        self._assert_table(table)
        known_cols = self._column_names(table)

        if columns:
            self._assert_columns(table, columns)
            select_cols = ", ".join(columns)
        else:
            select_cols = "*"

        try:
            limit_i = int(limit)
            offset_i = int(offset)
        except (TypeError, ValueError) as e:
            raise ValidationError("limit and offset must be integers") from e
        limit_i = max(1, min(limit_i, MAX_LIMIT))
        offset_i = max(0, offset_i)

        order_clause = ""
        if order_by:
            if order_by not in known_cols:
                raise ValidationError(f"unknown order_by column {order_by!r}")
            order_clause = f" ORDER BY {order_by} {'DESC' if descending else 'ASC'}"

        where_sql, where_params = self._build_where(table, filters)
        sql = f"SELECT {select_cols} FROM {table}{where_sql}{order_clause} LIMIT ? OFFSET ?"
        params = [*where_params, limit_i, offset_i]

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return {
            "table": table,
            "count": len(rows),
            "limit": limit_i,
            "offset": offset_i,
            "rows": [dict(r) for r in rows],
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict:
        self._assert_table(table)
        if not isinstance(values, dict) or not values:
            raise ValidationError("values must be a non-empty object of column→value")
        self._assert_columns(table, values.keys())

        cols = list(values.keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_list = ", ".join(cols)
        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

        with self.connect() as conn:
            cur = conn.execute(sql, [values[c] for c in cols])
            conn.commit()
            new_id = cur.lastrowid

        return {"table": table, "id": new_id, "values": values}

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: list[dict] | None = None,
        group_by: str | None = None,
    ) -> dict:
        self._assert_table(table)
        metric_l = (metric or "").lower()
        if metric_l not in ALLOWED_METRICS:
            raise ValidationError(
                f"unsupported metric {metric!r}; allowed: {sorted(ALLOWED_METRICS)}"
            )

        schema = {c["name"]: c for c in self.get_table_schema(table)}

        if metric_l == "count":
            target = column if column else "*"
            if column and column not in schema:
                raise ValidationError(f"unknown column {column!r} for table {table!r}")
            select_metric = f"COUNT({target})"
        else:
            if not column:
                raise ValidationError(f"metric {metric_l!r} requires a column")
            if column not in schema:
                raise ValidationError(f"unknown column {column!r} for table {table!r}")
            col_type = (schema[column]["type"] or "").upper()
            if not any(aff in col_type for aff in NUMERIC_AFFINITIES):
                raise ValidationError(
                    f"metric {metric_l!r} requires numeric column; "
                    f"{column!r} has type {schema[column]['type']!r}"
                )
            select_metric = f"{metric_l.upper()}({column})"

        group_clause = ""
        select_group = ""
        if group_by:
            if group_by not in schema:
                raise ValidationError(f"unknown group_by column {group_by!r}")
            select_group = f"{group_by} AS group_value, "
            group_clause = f" GROUP BY {group_by}"

        where_sql, where_params = self._build_where(table, filters)
        sql = (
            f"SELECT {select_group}{select_metric} AS value "
            f"FROM {table}{where_sql}{group_clause}"
        )

        with self.connect() as conn:
            rows = conn.execute(sql, where_params).fetchall()

        return {
            "table": table,
            "metric": metric_l,
            "column": column,
            "group_by": group_by,
            "rows": [dict(r) for r in rows],
        }
