"""Downstream-analysis export adapter."""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..artifacts import export_canonical_artifacts
from ..conditions import Condition
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

    validator = getattr(module, "validate_experiment_events", None)
    if not callable(validator):
        raise ValidationError(
            "design-research-analysis is installed but does not expose "
            "`integration.validate_experiment_events(...)`. Upgrade to the April "
            "compatibility branch."
        )

    report = validator(events_csv_path)
    if getattr(report, "is_valid", True):
        return

    errors = getattr(report, "errors", ())
    if isinstance(errors, Sequence) and not isinstance(errors, (str, bytes)):
        message = "; ".join(str(error) for error in errors) or "Unified table validation failed."
    else:
        message = "Unified table validation failed."
    raise ValidationError(message)


def _load_analysis_validation_module() -> Any | None:
    """Return the analysis integration module when the April API is available."""
    try:
        return importlib.import_module("design_research_analysis.integration")
    except ImportError as exc:
        try:
            importlib.import_module("design_research_analysis")
        except ImportError:
            return None
        raise ValidationError(
            "design-research-analysis is installed but does not expose the "
            "artifact-first `integration` module. Upgrade to the April compatibility "
            "branch."
        ) from exc


def validate_unified_event_columns(event_rows: Sequence[dict[str, Any]]) -> list[str]:
    """Validate that event rows include required unified-event columns."""
    errors: list[str] = []
    for index, row in enumerate(event_rows):
        for column in EVENT_REQUIRED_COLUMNS:
            if column not in row:
                errors.append(f"events row {index} is missing required column '{column}'.")
    return errors
