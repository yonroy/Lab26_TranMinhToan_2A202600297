"""Unit tests for the SQLite adapter."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import SQLiteAdapter, ValidationError  # noqa: E402
from init_db import create_database  # noqa: E402


@pytest.fixture()
def adapter(tmp_path):
    db_path = create_database(tmp_path / "test.db")
    return SQLiteAdapter(db_path)


def test_list_tables(adapter):
    assert set(adapter.list_tables()) == {"students", "courses", "enrollments"}


def test_get_table_schema(adapter):
    cols = {c["name"] for c in adapter.get_table_schema("students")}
    assert cols == {"id", "name", "cohort", "score"}


def test_search_with_filter_order_limit(adapter):
    out = adapter.search(
        table="students",
        filters=[{"column": "cohort", "op": "=", "value": "A1"}],
        order_by="score",
        descending=True,
        limit=2,
    )
    assert out["count"] == 2
    assert out["rows"][0]["score"] >= out["rows"][1]["score"]


def test_search_unknown_table(adapter):
    with pytest.raises(ValidationError):
        adapter.search(table="ghosts")


def test_search_unsupported_operator(adapter):
    with pytest.raises(ValidationError):
        adapter.search(
            table="students",
            filters=[{"column": "cohort", "op": "MATCH", "value": "A1"}],
        )


def test_insert_returns_id(adapter):
    out = adapter.insert(
        table="students",
        values={"name": "Test", "cohort": "A1", "score": 8.0},
    )
    assert isinstance(out["id"], int) and out["id"] > 0


def test_insert_empty_values(adapter):
    with pytest.raises(ValidationError):
        adapter.insert(table="students", values={})


def test_insert_unknown_column(adapter):
    with pytest.raises(ValidationError):
        adapter.insert(
            table="students",
            values={"name": "X", "cohort": "A1", "score": 1, "nope": True},
        )


def test_aggregate_count(adapter):
    out = adapter.aggregate(table="students", metric="count")
    assert out["rows"][0]["value"] == 8


def test_aggregate_avg_grouped(adapter):
    out = adapter.aggregate(
        table="students",
        metric="avg",
        column="score",
        group_by="cohort",
    )
    groups = {r["group_value"] for r in out["rows"]}
    assert groups == {"A1", "A2", "B1"}


def test_aggregate_avg_on_text_rejected(adapter):
    with pytest.raises(ValidationError):
        adapter.aggregate(table="students", metric="avg", column="name")


def test_aggregate_unknown_metric(adapter):
    with pytest.raises(ValidationError):
        adapter.aggregate(table="students", metric="median", column="score")
