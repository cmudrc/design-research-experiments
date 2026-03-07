"""Canonical artifact layout, manifest helpers, and checkpointing."""

from __future__ import annotations

import json
import tarfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .conditions import Condition
from .io import csv_io, json_io, sqlite_io, yaml_io
from .schemas import (
    SCHEMA_VERSION,
    Observation,
    RunStatus,
    stable_json_dumps,
    to_jsonable,
    utc_now_iso,
)
from .study import RunResult, Study, build_default_provenance

EVENT_COLUMNS_REQUIRED = (
    "timestamp",
    "record_id",
    "text",
    "session_id",
    "actor_id",
    "event_type",
    "meta_json",
)

RUN_COLUMNS_REQUIRED = (
    "study_id",
    "condition_id",
    "run_id",
    "problem_id",
    "problem_family",
    "agent_id",
    "agent_kind",
    "pattern_name",
    "model_name",
    "seed",
    "replicate",
    "status",
    "start_time",
    "end_time",
    "latency_s",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "primary_outcome",
    "trace_path",
    "manifest_path",
)

CONDITION_COLUMNS_REQUIRED = (
    "study_id",
    "condition_id",
    "admissible",
    "constraint_messages",
    "assignment_meta_json",
)

EVALUATION_COLUMNS_REQUIRED = (
    "run_id",
    "evaluator_id",
    "metric_name",
    "metric_value",
    "metric_unit",
    "aggregation_level",
    "notes_json",
)


@dataclass(slots=True)
class ArtifactPaths:
    """Resolved canonical artifact paths for one study output directory."""

    output_dir: Path
    study_yaml: Path
    manifest_json: Path
    conditions_csv: Path
    runs_csv: Path
    events_csv: Path
    evaluations_csv: Path
    hypotheses_json: Path
    analysis_plan_json: Path
    artifacts_dir: Path
    checkpoints_dir: Path


def canonical_artifact_paths(output_dir: str | Path) -> ArtifactPaths:
    """Return canonical artifact paths for one output directory."""
    base = Path(output_dir)
    artifacts_dir = base / "artifacts"
    checkpoints_dir = artifacts_dir / "checkpoints"
    return ArtifactPaths(
        output_dir=base,
        study_yaml=base / "study.yaml",
        manifest_json=base / "manifest.json",
        conditions_csv=base / "conditions.csv",
        runs_csv=base / "runs.csv",
        events_csv=base / "events.csv",
        evaluations_csv=base / "evaluations.csv",
        hypotheses_json=base / "hypotheses.json",
        analysis_plan_json=base / "analysis_plan.json",
        artifacts_dir=artifacts_dir,
        checkpoints_dir=checkpoints_dir,
    )


def initialize_artifact_layout(output_dir: str | Path) -> ArtifactPaths:
    """Ensure canonical artifact directories exist and return resolved paths."""
    paths = canonical_artifact_paths(output_dir)
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    paths.checkpoints_dir.mkdir(parents=True, exist_ok=True)
    return paths


def export_canonical_artifacts(
    *,
    study: Study,
    conditions: Sequence[Condition],
    run_results: Sequence[RunResult],
    output_dir: str | Path | None = None,
    include_sqlite: bool = False,
) -> dict[str, Path]:
    """Write the full canonical artifact contract for one study."""
    paths = initialize_artifact_layout(
        output_dir or study.output_dir or Path("artifacts") / study.study_id
    )

    yaml_io.write_yaml(paths.study_yaml, study.to_dict())

    manifest_payload = _build_manifest(study=study, run_results=run_results)
    json_io.write_json(paths.manifest_json, manifest_payload)

    conditions_rows = _conditions_rows(study=study, conditions=conditions)
    runs_rows = _runs_rows(study=study, run_results=run_results, manifest_path=paths.manifest_json)
    events_rows = _events_rows(run_results=run_results)
    evaluations_rows = _evaluation_rows(run_results=run_results)

    condition_fieldnames = _union_fieldnames(CONDITION_COLUMNS_REQUIRED, conditions_rows)
    run_fieldnames = _union_fieldnames(RUN_COLUMNS_REQUIRED, runs_rows)
    event_fieldnames = _union_fieldnames(EVENT_COLUMNS_REQUIRED, events_rows)
    evaluation_fieldnames = _union_fieldnames(EVALUATION_COLUMNS_REQUIRED, evaluations_rows)

    csv_io.write_csv(paths.conditions_csv, conditions_rows, fieldnames=condition_fieldnames)
    csv_io.write_csv(paths.runs_csv, runs_rows, fieldnames=run_fieldnames)
    csv_io.write_csv(paths.events_csv, events_rows, fieldnames=event_fieldnames)
    csv_io.write_csv(paths.evaluations_csv, evaluations_rows, fieldnames=evaluation_fieldnames)

    json_io.write_json(
        paths.hypotheses_json,
        [to_jsonable(hypothesis) for hypothesis in study.hypotheses],
    )
    json_io.write_json(
        paths.analysis_plan_json,
        [to_jsonable(plan) for plan in study.analysis_plans],
    )

    if include_sqlite:
        sqlite_io.mirror_tables_to_sqlite(
            paths.output_dir / "study.sqlite",
            tables={
                "conditions": conditions_rows,
                "runs": runs_rows,
                "events": events_rows,
                "evaluations": evaluations_rows,
            },
        )

    return {
        "study.yaml": paths.study_yaml,
        "manifest.json": paths.manifest_json,
        "conditions.csv": paths.conditions_csv,
        "runs.csv": paths.runs_csv,
        "events.csv": paths.events_csv,
        "evaluations.csv": paths.evaluations_csv,
        "hypotheses.json": paths.hypotheses_json,
        "analysis_plan.json": paths.analysis_plan_json,
        "artifacts": paths.artifacts_dir,
    }


def checkpoint_run_result(run_result: RunResult, *, output_dir: str | Path) -> Path:
    """Persist one run result checkpoint and append to JSONL ledger."""
    paths = initialize_artifact_layout(output_dir)

    run_payload = to_jsonable(run_result)
    per_run_path = paths.checkpoints_dir / f"{run_result.run_id}.json"
    json_io.write_json(per_run_path, run_payload)

    jsonl_path = paths.checkpoints_dir / "runs.jsonl"
    with jsonl_path.open("a", encoding="utf-8") as file_obj:
        file_obj.write(stable_json_dumps(run_payload))
        file_obj.write("\n")

    return per_run_path


def load_checkpointed_run_results(output_dir: str | Path) -> dict[str, RunResult]:
    """Load all checkpointed run results keyed by run ID."""
    paths = canonical_artifact_paths(output_dir)
    if not paths.checkpoints_dir.exists():
        return {}

    loaded: dict[str, RunResult] = {}
    for path in sorted(paths.checkpoints_dir.glob("*.json")):
        payload = json_io.read_json(path)
        run_result = _run_result_from_payload(payload)
        loaded[run_result.run_id] = run_result
    return loaded


def bundle_results(output_dir: str | Path, bundle_path: str | Path | None = None) -> Path:
    """Create a gzipped tar bundle from one study output directory."""
    output_path = Path(output_dir)
    resolved_bundle_path = Path(bundle_path) if bundle_path else output_path.with_suffix(".tar.gz")

    with tarfile.open(resolved_bundle_path, mode="w:gz") as archive:
        archive.add(output_path, arcname=output_path.name)
    return resolved_bundle_path


def _build_manifest(study: Study, run_results: Sequence[RunResult]) -> dict[str, Any]:
    """Build a provenance manifest payload."""
    status_counts: dict[str, int] = {}
    model_ids: set[str] = set()
    for run_result in run_results:
        status_key = (
            run_result.status.value
            if isinstance(run_result.status, RunStatus)
            else str(run_result.status)
        )
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
        model_name = run_result.provenance_info.get("model_name")
        if model_name:
            model_ids.add(str(model_name))

    provenance = dict(study.provenance_metadata)
    if not provenance:
        provenance = build_default_provenance()

    return {
        "schema_version": SCHEMA_VERSION,
        "study_id": study.study_id,
        "generated_at": utc_now_iso(),
        "status_counts": status_counts,
        "model_ids": sorted(model_ids),
        "run_count": len(run_results),
        "provenance": provenance,
    }


def _conditions_rows(study: Study, conditions: Sequence[Condition]) -> list[dict[str, Any]]:
    """Convert conditions into canonical `conditions.csv` rows."""
    rows: list[dict[str, Any]] = []
    for condition in conditions:
        row: dict[str, Any] = {
            "study_id": study.study_id,
            "condition_id": condition.condition_id,
            "admissible": condition.admissible,
            "constraint_messages": stable_json_dumps(condition.constraint_messages),
            "assignment_meta_json": stable_json_dumps(condition.metadata),
        }
        row.update(condition.factor_assignments)
        row.update({f"block_{key}": value for key, value in condition.block_assignments.items()})
        rows.append(row)
    return rows


def _runs_rows(
    *,
    study: Study,
    run_results: Sequence[RunResult],
    manifest_path: Path,
) -> list[dict[str, Any]]:
    """Convert run results into canonical `runs.csv` rows."""
    rows: list[dict[str, Any]] = []

    for run_result in run_results:
        run_spec = run_result.run_spec
        if run_spec is None:
            continue

        execution_metadata = run_spec.execution_metadata
        row = {
            "study_id": study.study_id,
            "condition_id": run_spec.condition_id,
            "run_id": run_result.run_id,
            "problem_id": run_spec.problem_id,
            "problem_family": execution_metadata.get("problem_family", "unknown"),
            "agent_id": execution_metadata.get("agent_id", str(run_spec.agent_spec_ref)),
            "agent_kind": execution_metadata.get("agent_kind", "unknown"),
            "pattern_name": execution_metadata.get("pattern_name", "unknown"),
            "model_name": execution_metadata.get("model_name", "unknown"),
            "seed": run_spec.seed,
            "replicate": run_spec.replicate,
            "status": run_result.status.value
            if isinstance(run_result.status, RunStatus)
            else str(run_result.status),
            "start_time": run_result.started_at,
            "end_time": run_result.ended_at,
            "latency_s": run_result.latency,
            "input_tokens": run_result.metrics.get("input_tokens", 0),
            "output_tokens": run_result.metrics.get("output_tokens", 0),
            "cost_usd": run_result.cost,
            "primary_outcome": run_result.metrics.get("primary_outcome"),
            "trace_path": run_result.trace_refs[0] if run_result.trace_refs else "",
            "manifest_path": str(manifest_path),
            "error_info": run_result.error_info,
        }
        rows.append(row)

    return rows


def _events_rows(run_results: Sequence[RunResult]) -> list[dict[str, Any]]:
    """Collect normalized event rows across all run results."""
    rows: list[dict[str, Any]] = []
    for run_result in run_results:
        for observation in run_result.observations:
            if isinstance(observation, Observation):
                rows.append(observation.to_row())
                continue

            if isinstance(observation, Mapping):
                row = dict(observation)
                row.setdefault("timestamp", utc_now_iso())
                row.setdefault("record_id", f"evt-{run_result.run_id}")
                row.setdefault("text", "")
                row.setdefault("session_id", run_result.run_id)
                row.setdefault("actor_id", "agent")
                row.setdefault("event_type", "event")
                row.setdefault("meta_json", "{}")
                if isinstance(row["meta_json"], Mapping):
                    row["meta_json"] = json.dumps(row["meta_json"], sort_keys=True)
                rows.append(row)
    return rows


def _evaluation_rows(run_results: Sequence[RunResult]) -> list[dict[str, Any]]:
    """Collect normalized evaluation rows across all run results."""
    rows: list[dict[str, Any]] = []
    for run_result in run_results:
        for row in run_result.evaluator_outputs:
            normalized = {
                "run_id": run_result.run_id,
                "evaluator_id": row.get("evaluator_id", "problem_evaluator"),
                "metric_name": row.get("metric_name", "score"),
                "metric_value": row.get("metric_value"),
                "metric_unit": row.get("metric_unit", "unitless"),
                "aggregation_level": row.get("aggregation_level", "run"),
                "notes_json": row.get("notes_json", {}),
            }
            if isinstance(normalized["notes_json"], Mapping):
                normalized["notes_json"] = json.dumps(normalized["notes_json"], sort_keys=True)
            rows.append(normalized)
    return rows


def _union_fieldnames(
    required_fields: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    """Build field names preserving required columns first."""
    ordered: list[str] = list(required_fields)
    seen = set(ordered)
    for row in rows:
        for key in row:
            if key in seen:
                continue
            ordered.append(key)
            seen.add(key)
    return tuple(ordered)


def _run_result_from_payload(payload: Mapping[str, Any]) -> RunResult:
    """Reconstruct a `RunResult` object from checkpoint JSON."""
    run_spec_payload = payload.get("run_spec")
    run_spec = None
    if isinstance(run_spec_payload, Mapping):
        run_spec = _run_spec_from_payload(run_spec_payload)

    status_raw = payload.get("status", RunStatus.PENDING.value)
    status = RunStatus(str(status_raw))

    observations_payload = payload.get("observations", [])
    observations: list[Any] = []
    if isinstance(observations_payload, Sequence):
        for item in observations_payload:
            if isinstance(item, Mapping):
                observations.append(dict(item))

    return RunResult(
        run_id=str(payload.get("run_id", "")),
        status=status,
        outputs=dict(payload.get("outputs", {})),
        metrics=dict(payload.get("metrics", {})),
        evaluator_outputs=[dict(row) for row in payload.get("evaluator_outputs", [])],
        cost=float(payload.get("cost", 0.0)),
        latency=float(payload.get("latency", 0.0)),
        trace_refs=[str(value) for value in payload.get("trace_refs", [])],
        artifact_refs=[str(value) for value in payload.get("artifact_refs", [])],
        error_info=payload.get("error_info"),
        provenance_info=dict(payload.get("provenance_info", {})),
        observations=observations,
        run_spec=run_spec,
        started_at=payload.get("started_at"),
        ended_at=payload.get("ended_at"),
    )


def _run_spec_from_payload(payload: Mapping[str, Any]) -> Any:
    """Reconstruct a `RunSpec` object from checkpoint JSON."""
    from .study import RunSpec

    return RunSpec(
        run_id=str(payload.get("run_id", "")),
        study_id=str(payload.get("study_id", "")),
        condition_id=str(payload.get("condition_id", "")),
        problem_id=str(payload.get("problem_id", "")),
        replicate=int(payload.get("replicate", 1)),
        seed=int(payload.get("seed", 0)),
        agent_spec_ref=payload.get("agent_spec_ref"),
        problem_spec_ref=payload.get("problem_spec_ref"),
        execution_metadata=dict(payload.get("execution_metadata", {})),
    )
