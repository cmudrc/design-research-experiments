"""YAML read/write helpers used for study definitions."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

yaml: Any | None
try:
    yaml = importlib.import_module("yaml")
except ImportError:  # pragma: no cover - dependency is required in normal installs.
    yaml = None


def write_yaml(path: Path, payload: Any) -> Path:
    """Write YAML payload with stable block style."""
    if yaml is None:
        raise RuntimeError("PyYAML is required for YAML serialization.")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        yaml.safe_dump(
            payload,
            stream=file_obj,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=False,
        )
    return path


def read_yaml(path: Path) -> dict[str, Any]:
    """Read YAML payload from disk."""
    if yaml is None:
        raise RuntimeError("PyYAML is required for YAML deserialization.")

    with path.open("r", encoding="utf-8") as file_obj:
        data = yaml.safe_load(file_obj)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise RuntimeError("Top-level YAML payload must be a mapping.")
    return data
