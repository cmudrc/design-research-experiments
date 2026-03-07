"""SQLite helpers for mirroring canonical artifact tables."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def mirror_tables_to_sqlite(
    sqlite_path: Path,
    *,
    tables: Mapping[str, Sequence[Mapping[str, Any]]],
) -> Path:
    """Mirror in-memory row tables into SQLite for large-study querying."""
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(sqlite_path) as connection:
        for table_name, rows in tables.items():
            _write_table(connection, table_name, rows)
    return sqlite_path


def _write_table(
    connection: sqlite3.Connection,
    table_name: str,
    rows: Sequence[Mapping[str, Any]],
) -> None:
    """Write one table to SQLite, replacing existing rows."""
    fieldnames = _discover_fieldnames(rows)
    if not fieldnames:
        return

    columns_clause = ", ".join(f'"{field}" TEXT' for field in fieldnames)
    connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    connection.execute(f'CREATE TABLE "{table_name}" ({columns_clause})')

    placeholders = ", ".join("?" for _ in fieldnames)
    insert_sql = f'INSERT INTO "{table_name}" ({", ".join(fieldnames)}) VALUES ({placeholders})'

    serialized_rows = [
        tuple(_serialize_cell(row.get(field)) for field in fieldnames) for row in rows
    ]
    connection.executemany(insert_sql, serialized_rows)
    connection.commit()


def _discover_fieldnames(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Collect an ordered union of all field names in the input rows."""
    names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key in seen:
                continue
            seen.add(key)
            names.append(key)
    return tuple(names)


def _serialize_cell(value: Any) -> str | None:
    """Serialize one SQLite cell to text or null."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=True)
