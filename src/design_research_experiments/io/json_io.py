"""JSON read/write helpers with deterministic formatting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: Any) -> Path:
    """Write JSON payload with stable formatting and UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, indent=2, sort_keys=True, ensure_ascii=True)
        file_obj.write("\n")
    return path


def read_json(path: Path) -> Any:
    """Read JSON payload from disk."""
    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)
