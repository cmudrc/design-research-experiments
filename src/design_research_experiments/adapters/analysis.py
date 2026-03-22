"""Downstream-analysis export adapter."""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..artifacts import export_canonical_artifacts
from ..conditions import Condition
from ..io import csv_io
from ..schemas import ValidationError
from ..study import RunResult, Study

EVENT_REQUIRED_COLUMNS = (
    "timestamp",
    "record_id",
    "text",
    "session_id",
    "actor_id",
    "event_type",
    "meta_json",
)


def export_analysis_tables(
    study: Study,
    *,
    conditions: Sequence[Condition],
    run_results: Sequence[RunResult],
    output_dir: str | Path | None = None,
    include_sqlite: bool = False,
    validate_with_analysis_package: bool = False,
) -> dict[str, Path]:
    """Export canonical analysis tables aligned with downstream workflows."""
    paths = export_canonical_artifacts(
        study=study,
        conditions=conditions,
        run_results=run_results,
        output_dir=output_dir,
        include_sqlite=include_sqlite,
    )

    if validate_with_analysis_package:
        _run_optional_analysis_validation(paths["events.csv"])

    return paths


def _run_optional_analysis_validation(events_csv_path: Path) -> None:
    """Optionally run validation hooks from design-research-analysis when available."""
    module = _load_analysis_validation_module()
    if module is None:
        return

    validator = getattr(module, "validate_unified_table", None)
    if not callable(validator):
        return

    rows = csv_io.read_csv(events_csv_path)
    coerce = getattr(module, "coerce_unified_table", None)
    table = coerce(rows) if callable(coerce) else rows
    report = validator(table)
    if getattr(report, "is_valid", True):
        return

    errors = getattr(report, "errors", ())
    if isinstance(errors, Sequence) and not isinstance(errors, (str, bytes)):
        message = "; ".join(str(error) for error in errors) or "Unified table validation failed."
    else:
        message = "Unified table validation failed."
    raise ValidationError(message)


def _load_analysis_validation_module() -> Any | None:
    """Return the first analysis module export surface with unified-table validators."""
    for module_name in ("design_research_analysis", "design_research_analysis.table"):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        if hasattr(module, "validate_unified_table"):
            return module
    return None


def validate_unified_event_columns(event_rows: Sequence[dict[str, Any]]) -> list[str]:
    """Validate that event rows include required unified-event columns."""
    errors: list[str] = []
    for index, row in enumerate(event_rows):
        for column in EVENT_REQUIRED_COLUMNS:
            if column not in row:
                errors.append(f"events row {index} is missing required column '{column}'.")
    return errors
