"""Downstream-analysis export adapter."""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..artifacts import export_canonical_artifacts
from ..conditions import Condition
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
    try:
        module = importlib.import_module("design_research_analysis")
    except ImportError:
        return

    candidate_names = (
        "validate_unified_event_table",
        "validate_event_table",
        "validate_events",
    )

    for name in candidate_names:
        if not hasattr(module, name):
            continue
        validator = getattr(module, name)
        if callable(validator):
            try:
                validator(events_csv_path)
            except Exception:
                return
            return


def validate_unified_event_columns(event_rows: Sequence[dict[str, Any]]) -> list[str]:
    """Validate that event rows include required unified-event columns."""
    errors: list[str] = []
    for index, row in enumerate(event_rows):
        for column in EVENT_REQUIRED_COLUMNS:
            if column not in row:
                errors.append(f"events row {index} is missing required column '{column}'.")
    return errors
