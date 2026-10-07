"""Durable, versioned evidence records for individual study runs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

from .schemas import RunStatus, ValidationError, stable_json_dumps, to_jsonable
from .study import RunResult, RunSpec

RUN_EVIDENCE_SCHEMA_VERSION = "0.1.0"
RUN_EVIDENCE_RECORD_TYPE = "run-evidence"
REDACTED_VALUE = "[REDACTED]"

_TERMINAL_STATUSES = frozenset(
    {
        RunStatus.SUCCESS,
        RunStatus.FAILED,
        RunStatus.SKIPPED,
    }
)
_ATTEMPTED_STATUSES = frozenset(
    {
        RunStatus.RUNNING,
        RunStatus.SUCCESS,
        RunStatus.FAILED,
    }
)
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "bearer_token",
        "client_secret",
        "credential",
        "credentials",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "access_token",
    }
)
_SENSITIVE_SUFFIXES = (
    "_api_key",
    "_access_token",
    "_refresh_token",
    "_password",
    "_secret",
    "_credential",
    "_credentials",
    "_private_key",
)
_SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token)\s*[:=]\s*\S+"),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{20,})\b"),
)
_REQUIRED_RECORD_KEYS = frozenset(
    {
        "schema_version",
        "record_type",
        "study_id",
        "condition_id",
        "run_id",
        "status",
        "status_reason",
        "attempted",
        "terminal",
        "configured",
        "observed",
        "timing",
        "error",
        "files",
        "integrity",
    }
)


def initialize_run_evidence(run_spec: RunSpec, *, output_dir: str | Path) -> Path:
    """Persist a planned run before execution begins."""
    return _write_evidence_record(
        RunResult(
            run_id=run_spec.run_id,
            status=RunStatus.PENDING,
            run_spec=run_spec,
            status_reason="awaiting_execution",
        ),
        output_dir=output_dir,
    )


def mark_run_evidence_running(
    run_spec: RunSpec,
    *,
    output_dir: str | Path,
    started_at: str,
) -> Path:
    """Persist that a planned run reached its execution boundary."""
    return _write_evidence_record(
        RunResult(
            run_id=run_spec.run_id,
            status=RunStatus.RUNNING,
            run_spec=run_spec,
            started_at=started_at,
            status_reason="execution_started",
        ),
        output_dir=output_dir,
    )


def write_run_evidence(run_result: RunResult, *, output_dir: str | Path) -> Path:
    """Persist the latest evidence state for one run atomically."""
    return _write_evidence_record(run_result, output_dir=output_dir)


def load_run_evidence_records(output_dir: str | Path) -> dict[str, dict[str, Any]]:
    """Load and validate all durable run-evidence records in a study directory."""
    runs_dir = _runs_dir(output_dir)
    if not runs_dir.exists():
        return {}

    records: dict[str, dict[str, Any]] = {}
    for run_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
        run_path = run_dir / "run.json"
        if not run_path.is_file():
            raise ValidationError(
                f"Incomplete run-evidence directory is missing run.json: {run_dir}."
            )
        payload = _read_json(run_path)
        _validate_run_evidence(payload, expected_run_id=run_dir.name)
        _validate_evidence_files(Path(output_dir), run_dir, payload)
        run_id = str(payload["run_id"])
        records[run_id] = payload
    return records


def _write_evidence_record(run_result: RunResult, *, output_dir: str | Path) -> Path:
    """Write one complete lifecycle snapshot and its observation stream."""
    run_spec = run_result.run_spec
    if run_spec is None:
        raise ValidationError("Run evidence requires RunResult.run_spec.")
    if run_result.run_id != run_spec.run_id:
        raise ValidationError(
            "RunResult.run_id must match RunResult.run_spec.run_id for evidence persistence."
        )

    run_dir = _run_dir(output_dir, run_result.run_id)
    attachments_dir = run_dir / "attachments"
    observations_path = run_dir / "observations.jsonl"
    run_path = run_dir / "run.json"
    attachments_dir.mkdir(parents=True, exist_ok=True)

    observations_text = _observations_jsonl(run_result.observations)
    _atomic_write_text(observations_path, observations_text)

    payload = _build_run_evidence_payload(
        run_result,
        output_dir=Path(output_dir),
        observations_sha256=_sha256_text(observations_text),
    )
    _atomic_write_text(run_path, _pretty_json(payload))
    return run_path


def _build_run_evidence_payload(
    run_result: RunResult,
    *,
    output_dir: Path,
    observations_sha256: str,
) -> dict[str, Any]:
    """Build the versioned and redacted JSON record for one run state."""
    run_spec = run_result.run_spec
    if run_spec is None:  # pragma: no cover - guarded by _write_evidence_record
        raise ValidationError("Run evidence requires RunResult.run_spec.")

    status = _coerce_status(run_result.status)
    referenced_artifacts = _referenced_artifacts(
        output_dir=output_dir,
        trace_refs=run_result.trace_refs,
        artifact_refs=run_result.artifact_refs,
    )

    payload = {
        "schema_version": RUN_EVIDENCE_SCHEMA_VERSION,
        "record_type": RUN_EVIDENCE_RECORD_TYPE,
        "study_id": run_spec.study_id,
        "condition_id": run_spec.condition_id,
        "run_id": run_result.run_id,
        "status": status.value,
        "status_reason": run_result.status_reason or _default_status_reason(status),
        "attempted": status in _ATTEMPTED_STATUSES,
        "terminal": status in _TERMINAL_STATUSES,
        "configured": {
            "problem_id": run_spec.problem_id,
            "problem_spec_ref": run_spec.problem_spec_ref,
            "agent_spec_ref": run_spec.agent_spec_ref,
            "replicate": run_spec.replicate,
            "seed": run_spec.seed,
            "execution_metadata": (
                run_result.configured_execution_metadata or run_spec.execution_metadata
            ),
        },
        "observed": {
            "execution_metadata": run_result.observed_execution_metadata,
            "outputs": run_result.outputs,
            "metrics": run_result.metrics,
            "evaluations": run_result.evaluator_outputs,
            "provenance": _normalize_provenance(run_result.provenance_info),
            "trace_refs": run_result.trace_refs,
            "artifact_refs": run_result.artifact_refs,
            "observation_count": len(run_result.observations),
        },
        "timing": {
            "started_at": run_result.started_at,
            "ended_at": run_result.ended_at,
            "latency_s": run_result.latency,
        },
        "error": run_result.error_info,
        "files": {
            "observations": "observations.jsonl",
            "attachments": "attachments",
        },
        "integrity": {
            "observations_sha256": observations_sha256,
            "referenced_artifacts": referenced_artifacts,
        },
    }
    return cast(dict[str, Any], _redact_sensitive(payload))


def _default_status_reason(status: RunStatus) -> str:
    """Return the default machine-readable reason for a lifecycle state."""
    reasons = {
        RunStatus.PENDING: "awaiting_execution",
        RunStatus.RUNNING: "execution_started",
        RunStatus.SUCCESS: "completed",
        RunStatus.FAILED: "exception",
        RunStatus.SKIPPED: "not_executed",
    }
    return reasons[status]


def _coerce_status(status: RunStatus | str) -> RunStatus:
    """Normalize a run status and reject values outside the public lifecycle."""
    try:
        return status if isinstance(status, RunStatus) else RunStatus(str(status))
    except ValueError as exc:
        raise ValidationError(f"Unsupported run-evidence status: {status!r}.") from exc


def _observations_jsonl(observations: Sequence[Any]) -> str:
    """Serialize redacted observations as deterministic JSON Lines."""
    lines = [stable_json_dumps(_redact_sensitive(observation)) for observation in observations]
    return "" if not lines else "\n".join(lines) + "\n"


def _normalize_provenance(provenance: Mapping[str, Any]) -> dict[str, Any]:
    """Recover structured execution metadata before recursive redaction."""
    normalized = dict(provenance)
    execution_metadata = normalized.get("execution_metadata")
    if isinstance(execution_metadata, str):
        try:
            decoded = json.loads(execution_metadata)
        except json.JSONDecodeError:
            return normalized
        if isinstance(decoded, Mapping):
            normalized["execution_metadata"] = dict(decoded)
    return normalized


def _referenced_artifacts(
    *,
    output_dir: Path,
    trace_refs: Sequence[str],
    artifact_refs: Sequence[str],
) -> list[dict[str, Any]]:
    """Describe trace and artifact references with safe local hashes."""
    records: list[dict[str, Any]] = []
    for kind, references in (("trace", trace_refs), ("artifact", artifact_refs)):
        for reference in references:
            records.append(
                {
                    "kind": kind,
                    "reference": str(reference),
                    "sha256": _hash_local_reference(output_dir, str(reference)),
                }
            )
    return records


def _hash_local_reference(output_dir: Path, reference: str) -> str | None:
    """Hash a file only when it resolves inside the study directory."""
    referenced_path = Path(reference)
    candidate = referenced_path if referenced_path.is_absolute() else output_dir / referenced_path
    try:
        resolved_output = output_dir.resolve()
        resolved_candidate = candidate.resolve()
        resolved_candidate.relative_to(resolved_output)
    except (OSError, ValueError):
        return None
    if not resolved_candidate.is_file():
        return None
    return hashlib.sha256(resolved_candidate.read_bytes()).hexdigest()


def _redact_sensitive(value: Any) -> Any:
    """Recursively replace values associated with known credential keys."""
    jsonable = to_jsonable(value)
    if isinstance(jsonable, Mapping):
        redacted: dict[str, Any] = {}
        for raw_key, item in jsonable.items():
            key = str(raw_key)
            redacted[key] = REDACTED_VALUE if _is_sensitive_key(key) else _redact_sensitive(item)
        return redacted
    if isinstance(jsonable, list):
        return [_redact_sensitive(item) for item in jsonable]
    if isinstance(jsonable, str):
        for pattern in _SENSITIVE_TEXT_PATTERNS:
            jsonable = pattern.sub(REDACTED_VALUE, jsonable)
    return jsonable


def _is_sensitive_key(key: str) -> bool:
    """Return whether a mapping key conventionally denotes a credential."""
    normalized = key.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized in _SENSITIVE_KEYS or normalized.endswith(_SENSITIVE_SUFFIXES)


def _validate_run_evidence(payload: Any, *, expected_run_id: str) -> None:
    """Validate one run record against schema and lifecycle invariants."""
    if not isinstance(payload, Mapping):
        raise ValidationError("run.json must contain a JSON object.")
    missing = sorted(_REQUIRED_RECORD_KEYS - payload.keys())
    if missing:
        raise ValidationError(f"run.json is missing required keys: {', '.join(missing)}.")
    if payload["schema_version"] != RUN_EVIDENCE_SCHEMA_VERSION:
        raise ValidationError(
            "run.json schema_version "
            f"{payload['schema_version']!r} does not match {RUN_EVIDENCE_SCHEMA_VERSION!r}."
        )
    if payload["record_type"] != RUN_EVIDENCE_RECORD_TYPE:
        raise ValidationError(f"run.json record_type must be {RUN_EVIDENCE_RECORD_TYPE!r}.")
    run_id = str(payload["run_id"])
    _validate_run_id(run_id)
    if run_id != expected_run_id:
        raise ValidationError(
            f"run.json run_id {run_id!r} does not match directory {expected_run_id!r}."
        )
    status = _coerce_status(str(payload["status"]))
    if not str(payload["study_id"]).strip():
        raise ValidationError("run.json study_id must be non-empty.")
    if not str(payload["condition_id"]).strip():
        raise ValidationError("run.json condition_id must be non-empty.")
    if not isinstance(payload["status_reason"], str) or not payload["status_reason"].strip():
        raise ValidationError("run.json status_reason must be a non-empty string.")
    if payload["attempted"] is not (status in _ATTEMPTED_STATUSES):
        raise ValidationError("run.json attempted does not match its lifecycle status.")
    if payload["terminal"] is not (status in _TERMINAL_STATUSES):
        raise ValidationError("run.json terminal does not match its lifecycle status.")
    if not isinstance(payload["configured"], Mapping):
        raise ValidationError("run.json configured must be a JSON object.")
    if not isinstance(payload["observed"], Mapping):
        raise ValidationError("run.json observed must be a JSON object.")
    if not isinstance(payload["files"], Mapping):
        raise ValidationError("run.json files must be a JSON object.")
    if not isinstance(payload["integrity"], Mapping):
        raise ValidationError("run.json integrity must be a JSON object.")


def _validate_evidence_files(
    output_dir: Path,
    run_dir: Path,
    payload: Mapping[str, Any],
) -> None:
    """Validate fixed companion paths and the observation-stream hash."""
    files = payload["files"]
    integrity = payload["integrity"]
    if not isinstance(files, Mapping) or not isinstance(integrity, Mapping):
        raise ValidationError("run.json files and integrity must be JSON objects.")
    if files.get("observations") != "observations.jsonl":
        raise ValidationError("run.json observations path must be 'observations.jsonl'.")
    if files.get("attachments") != "attachments":
        raise ValidationError("run.json attachments path must be 'attachments'.")

    observations_path = run_dir / "observations.jsonl"
    attachments_path = run_dir / "attachments"
    if not observations_path.is_file():
        raise ValidationError(f"Missing run-evidence observations file: {observations_path}.")
    if not attachments_path.is_dir():
        raise ValidationError(f"Missing run-evidence attachments directory: {attachments_path}.")

    expected_hash = integrity.get("observations_sha256")
    actual_hash = hashlib.sha256(observations_path.read_bytes()).hexdigest()
    if expected_hash != actual_hash:
        raise ValidationError(f"Run-evidence observation hash mismatch for {payload['run_id']!r}.")

    referenced_artifacts = integrity.get("referenced_artifacts")
    if not isinstance(referenced_artifacts, list):
        raise ValidationError("run.json referenced_artifacts must be a JSON array.")
    for reference_record in referenced_artifacts:
        if not isinstance(reference_record, Mapping):
            raise ValidationError("run.json referenced artifact entries must be JSON objects.")
        expected_reference_hash = reference_record.get("sha256")
        if expected_reference_hash is None:
            continue
        reference = str(reference_record.get("reference", ""))
        actual_reference_hash = _hash_local_reference(output_dir, reference)
        if expected_reference_hash != actual_reference_hash:
            raise ValidationError(f"Run-evidence artifact hash mismatch for {reference!r}.")


def _runs_dir(output_dir: str | Path) -> Path:
    """Return the stable directory containing per-run evidence."""
    return Path(output_dir) / "artifacts" / "runs"


def _run_dir(output_dir: str | Path, run_id: str) -> Path:
    """Return the evidence directory for one validated run identifier."""
    _validate_run_id(run_id)
    return _runs_dir(output_dir) / run_id


def _validate_run_id(run_id: str) -> None:
    """Reject run identifiers that could escape the evidence directory."""
    if not run_id or run_id in {".", ".."} or Path(run_id).name != run_id or "\\" in run_id:
        raise ValidationError(f"run_id {run_id!r} is not safe for evidence paths.")


def _pretty_json(payload: Any) -> str:
    """Serialize one human-readable deterministic JSON document."""
    return json.dumps(to_jsonable(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _read_json(path: Path) -> Any:
    """Read one UTF-8 JSON document."""
    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def _sha256_text(content: str) -> str:
    """Return the SHA-256 digest for UTF-8 text."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _atomic_write_text(path: Path, content: str) -> None:
    """Write text through a flushed temporary file and atomic replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as file_obj:
            file_obj.write(content)
            file_obj.flush()
            os.fsync(file_obj.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        with suppress(OSError):
            os.close(file_descriptor)
        temporary_path.unlink(missing_ok=True)
        raise
