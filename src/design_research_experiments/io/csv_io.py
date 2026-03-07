"""CSV read/write helpers for canonical artifact tables."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def write_csv(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    fieldnames: Sequence[str] | None = None,
) -> Path:
    """Write rows to CSV while preserving a deterministic column order."""
    path.parent.mkdir(parents=True, exist_ok=True)

    resolved_fieldnames = list(fieldnames or _discover_fieldnames(rows))
    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=resolved_fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in resolved_fieldnames})

    return path


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read CSV rows as string-valued dictionaries."""
    with path.open("r", encoding="utf-8", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        return [dict(row) for row in reader]


def _discover_fieldnames(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Discover field names from an ordered union of row keys."""
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key in seen:
                continue
            seen.add(key)
            keys.append(key)
    return tuple(keys)
