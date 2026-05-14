"""Create and seed the SQLite database used by the FastMCP server."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name   TEXT    NOT NULL,
    cohort TEXT    NOT NULL,
    score  REAL    NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS courses (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    code    TEXT    NOT NULL UNIQUE,
    title   TEXT    NOT NULL,
    credits INTEGER NOT NULL DEFAULT 3
);

CREATE TABLE IF NOT EXISTS enrollments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    course_id  INTEGER NOT NULL REFERENCES courses(id),
    grade      TEXT
);
"""

SEED_STUDENTS = [
    ("Alice Nguyen",  "A1", 9.1),
    ("Bao Tran",      "A1", 8.4),
    ("Chau Pham",     "A2", 7.6),
    ("Dung Le",       "A2", 8.9),
    ("Emily Vu",      "B1", 6.8),
    ("Felix Hoang",   "B1", 7.2),
    ("Giang Do",      "A1", 9.5),
    ("Huy Bui",       "A2", 5.9),
]

SEED_COURSES = [
    ("CS101", "Intro to CS",        3),
    ("CS201", "Data Structures",    4),
    ("ML301", "Machine Learning",   4),
    ("DB210", "Databases",          3),
]

SEED_ENROLLMENTS = [
    (1, 1, "A"), (1, 2, "A-"),
    (2, 1, "B+"), (2, 3, "B"),
    (3, 2, "A"), (3, 4, "B+"),
    (4, 3, "A-"), (4, 4, "A"),
    (5, 1, "C+"), (6, 2, "B"),
    (7, 3, "A"), (7, 4, "A"),
    (8, 1, "C"),
]


def _has_rows(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
    return row[0] > 0


def create_database(path: str | os.PathLike | None = None) -> str:
    """Create schema + seed data if the DB file is empty. Returns absolute path."""
    db_path = Path(path or os.environ.get("DB_PATH") or "data/students.db").resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)

        if not _has_rows(conn, "students"):
            conn.executemany(
                "INSERT INTO students(name, cohort, score) VALUES (?,?,?)",
                SEED_STUDENTS,
            )
        if not _has_rows(conn, "courses"):
            conn.executemany(
                "INSERT INTO courses(code, title, credits) VALUES (?,?,?)",
                SEED_COURSES,
            )
        if not _has_rows(conn, "enrollments"):
            conn.executemany(
                "INSERT INTO enrollments(student_id, course_id, grade) VALUES (?,?,?)",
                SEED_ENROLLMENTS,
            )
        conn.commit()
    finally:
        conn.close()

    return str(db_path)


if __name__ == "__main__":
    print(create_database())
