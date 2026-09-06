"""Tests for durable per-run evidence and runner lifecycle accounting."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
from copy import deepcopy
from pathlib import Path

import pytest

from design_research_experiments import evidence as evidence_module
from design_research_experiments import load_run_evidence_records
from design_research_experiments import runners as runner_module
from design_research_experiments.conditions import Condition, Factor, FactorKind, Level
from design_research_experiments.evidence import (
    REDACTED_VALUE,
    RUN_EVIDENCE_RECORD_TYPE,
    RUN_EVIDENCE_SCHEMA_VERSION,
    write_run_evidence,
)
from design_research_experiments.runners import RunOutput, run_study
from design_research_experiments.schemas import RunBudget, RunStatus, ValidationError
from design_research_experiments.study import RunResult, RunSpec

from .helpers import make_study


def test_write_run_evidence_preserves_structure_hashes_and_redacts_secrets(
    tmp_path: Path,
) -> None:
    """One run record should be portable, integrity-aware, and safe to share."""
    output_dir = tmp_path / "evidence-study"
    referenced_path = output_dir / "artifacts" / "raw-output.txt"
    referenced_path.parent.mkdir(parents=True)
    referenced_path.write_text("retained raw output\n", encoding="utf-8")

    run_spec = RunSpec(
        run_id="run-safe",
        study_id="evidence-study",
        condition_id="condition-a",
        problem_id="problem-a",
        replicate=2,
        seed=41,
        agent_spec_ref="agent-a",
        problem_spec_ref="problem-a",
        execution_metadata={
            "condition_fingerprint": "condition-hash",
            "api_key": "configured-secret",
            "model_name": "configured-model",
            "nested": {"client-secret": "nested-secret"},
        },
    )
    result = RunResult(
        run_id=run_spec.run_id,
        status=RunStatus.SUCCESS,
        outputs={
            "text": "answer from sk-1234567890abcdef",
            "private_key": "output-secret",
        },
        metrics={"input_tokens": 12, "primary_outcome": 0.8},
        evaluator_outputs=[{"metric_name": "score", "metric_value": 0.8}],
        artifact_refs=[
            "artifacts/raw-output.txt",
            "../outside.txt",
            "artifacts/missing.txt",
        ],
        provenance_info={
            "authorization": "Bearer secret",
            "request_id": "request-1",
            "execution_metadata": json.dumps({"api_key": "serialized-secret"}),
        },
        observations=[
            {
                "event_type": "tool-call",
                "text": "observed with Bearer sensitive-token-value",
                "metadata": {"password": "observation-secret", "token_count": 9},
            }
        ],
        run_spec=run_spec,
        started_at="2026-09-06T12:00:00+00:00",
        ended_at="2026-09-06T12:00:01+00:00",
        latency=1.0,
        configured_execution_metadata={
            "condition_fingerprint": "condition-hash",
            "api_key": "configured-secret",
            "model_name": "configured-model",
            "nested": {"client-secret": "nested-secret"},
        },
        observed_execution_metadata={"model_name": "observed-model"},
    )

    run_path = write_run_evidence(result, output_dir=output_dir)
    observations_path = run_path.parent / "observations.jsonl"
    record = json.loads(run_path.read_text(encoding="utf-8"))
    observations_text = observations_path.read_text(encoding="utf-8")

    assert record["schema_version"] == RUN_EVIDENCE_SCHEMA_VERSION
    assert record["record_type"] == RUN_EVIDENCE_RECORD_TYPE
    assert record["status"] == "success"
    assert record["status_reason"] == "completed"
    assert record["attempted"] is True
    assert record["terminal"] is True
    assert record["configured"]["execution_metadata"]["api_key"] == REDACTED_VALUE
    assert record["configured"]["execution_metadata"]["nested"]["client-secret"] == (REDACTED_VALUE)
    assert record["configured"]["execution_metadata"]["model_name"] == "configured-model"
    assert record["observed"]["execution_metadata"] == {"model_name": "observed-model"}
    assert record["observed"]["outputs"]["private_key"] == REDACTED_VALUE
    assert "sk-1234567890abcdef" not in record["observed"]["outputs"]["text"]
    assert record["observed"]["metrics"]["input_tokens"] == 12
    assert record["observed"]["provenance"]["authorization"] == REDACTED_VALUE
    assert record["observed"]["provenance"]["execution_metadata"]["api_key"] == (REDACTED_VALUE)
    assert "observation-secret" not in observations_text
    assert "sensitive-token-value" not in observations_text
    assert '"token_count":9' in observations_text
    assert (
        record["integrity"]["observations_sha256"]
        == hashlib.sha256(observations_text.encode("utf-8")).hexdigest()
    )

    references = record["integrity"]["referenced_artifacts"]
    assert references[0]["sha256"] == hashlib.sha256(referenced_path.read_bytes()).hexdigest()
    assert references[1]["sha256"] is None
    assert references[2]["sha256"] is None
    assert (run_path.parent / "attachments").is_dir()
    assert load_run_evidence_records(output_dir) == {run_spec.run_id: record}

    referenced_path.write_text("changed raw output\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="artifact hash mismatch"):
        load_run_evidence_records(output_dir)
    referenced_path.write_text("retained raw output\n", encoding="utf-8")

    observations_path.write_text(observations_text + "{}\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="observation hash mismatch"):
        load_run_evidence_records(output_dir)


def test_evidence_rejects_missing_specs_unsafe_ids_and_invalid_records(tmp_path: Path) -> None:
    """Evidence paths and records should fail loudly instead of drifting silently."""
    with pytest.raises(ValidationError, match=r"requires RunResult\.run_spec"):
        write_run_evidence(
            RunResult(run_id="missing-spec", status=RunStatus.SUCCESS),
            output_dir=tmp_path,
        )

    unsafe_spec = RunSpec(
        run_id="../unsafe",
        study_id="study",
        condition_id="condition",
        problem_id="problem",
        replicate=1,
        seed=1,
        agent_spec_ref="agent",
        problem_spec_ref="problem",
    )
    with pytest.raises(ValidationError, match="not safe for evidence paths"):
        write_run_evidence(
            RunResult(run_id=unsafe_spec.run_id, status=RunStatus.SUCCESS, run_spec=unsafe_spec),
            output_dir=tmp_path,
        )

    invalid_dir = tmp_path / "artifacts" / "runs" / "run-invalid"
    invalid_dir.mkdir(parents=True)
    (invalid_dir / "run.json").write_text('{"schema_version": "0.1.0"}\n', encoding="utf-8")
    with pytest.raises(ValidationError, match="missing required keys"):
        load_run_evidence_records(tmp_path)

    (invalid_dir / "run.json").unlink()
    with pytest.raises(ValidationError, match="Incomplete run-evidence directory"):
        load_run_evidence_records(tmp_path)


def test_evidence_rejects_inconsistent_or_drifted_record_fields(tmp_path: Path) -> None:
    """The loader should enforce identity, lifecycle, and object-shape invariants."""
    run_spec = RunSpec(
        run_id="run-validated",
        study_id="validated-study",
        condition_id="condition-a",
        problem_id="problem-a",
        replicate=1,
        seed=1,
        agent_spec_ref="agent-a",
        problem_spec_ref="problem-a",
    )
    run_path = write_run_evidence(
        RunResult(run_id=run_spec.run_id, status=RunStatus.SUCCESS, run_spec=run_spec),
        output_dir=tmp_path,
    )
    valid_record = json.loads(run_path.read_text(encoding="utf-8"))
    cases = [
        ("schema_version", "9.9.9", "schema_version"),
        ("record_type", "other", "record_type"),
        ("run_id", "other-run", "does not match directory"),
        ("status", "unknown", "Unsupported run-evidence status"),
        ("study_id", "", "study_id must be non-empty"),
        ("condition_id", "", "condition_id must be non-empty"),
        ("status_reason", "", "status_reason must be a non-empty string"),
        ("attempted", False, "attempted does not match"),
        ("terminal", False, "terminal does not match"),
        ("configured", [], "configured must be a JSON object"),
        ("observed", [], "observed must be a JSON object"),
        ("files", [], "files must be a JSON object"),
        ("integrity", [], "integrity must be a JSON object"),
    ]
    for field, value, message in cases:
        mutated = deepcopy(valid_record)
        mutated[field] = value
        run_path.write_text(json.dumps(mutated), encoding="utf-8")
        with pytest.raises(ValidationError, match=message):
            load_run_evidence_records(tmp_path)

    run_path.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="must contain a JSON object"):
        load_run_evidence_records(tmp_path)


def test_evidence_rejects_drifted_or_missing_companion_paths(tmp_path: Path) -> None:
    """Companion files are fixed by schema and verified before records are returned."""
    run_spec = RunSpec(
        run_id="run-files",
        study_id="files-study",
        condition_id="condition-a",
        problem_id="problem-a",
        replicate=1,
        seed=1,
        agent_spec_ref="agent-a",
        problem_spec_ref="problem-a",
    )
    run_path = write_run_evidence(
        RunResult(run_id=run_spec.run_id, status=RunStatus.SUCCESS, run_spec=run_spec),
        output_dir=tmp_path,
    )
    record = json.loads(run_path.read_text(encoding="utf-8"))

    record["files"]["observations"] = "other.jsonl"
    run_path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValidationError, match="observations path"):
        load_run_evidence_records(tmp_path)

    record["files"]["observations"] = "observations.jsonl"
    record["files"]["attachments"] = "other"
    run_path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValidationError, match="attachments path"):
        load_run_evidence_records(tmp_path)

    record["files"]["attachments"] = "attachments"
    run_path.write_text(json.dumps(record), encoding="utf-8")
    observations_path = run_path.parent / "observations.jsonl"
    observations_path.unlink()
    with pytest.raises(ValidationError, match="Missing run-evidence observations"):
        load_run_evidence_records(tmp_path)

    observations_path.write_text("", encoding="utf-8")
    (run_path.parent / "attachments").rmdir()
    with pytest.raises(ValidationError, match="Missing run-evidence attachments"):
        load_run_evidence_records(tmp_path)


def test_writer_rejects_mismatched_identity_and_cleans_failed_atomic_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A partial write must not masquerade as a completed evidence file."""
    run_spec = RunSpec(
        run_id="run-identity",
        study_id="identity-study",
        condition_id="condition-a",
        problem_id="problem-a",
        replicate=1,
        seed=1,
        agent_spec_ref="agent-a",
        problem_spec_ref="problem-a",
    )
    with pytest.raises(ValidationError, match="must match"):
        write_run_evidence(
            RunResult(run_id="different-run", status=RunStatus.SUCCESS, run_spec=run_spec),
            output_dir=tmp_path,
        )

    monkeypatch.setattr(
        evidence_module.os,
        "replace",
        lambda _source, _target: (_ for _ in ()).throw(OSError("replace failed")),
    )
    with pytest.raises(OSError, match="replace failed"):
        write_run_evidence(
            RunResult(run_id=run_spec.run_id, status=RunStatus.SUCCESS, run_spec=run_spec),
            output_dir=tmp_path,
        )
    assert not list((tmp_path / "artifacts" / "runs" / run_spec.run_id).glob("*.tmp"))


def test_non_json_execution_metadata_remains_visible(tmp_path: Path) -> None:
    """Legacy provenance strings should survive when they are not JSON objects."""
    run_spec = RunSpec(
        run_id="run-legacy-provenance",
        study_id="legacy-study",
        condition_id="condition-a",
        problem_id="problem-a",
        replicate=1,
        seed=1,
        agent_spec_ref="agent-a",
        problem_spec_ref="problem-a",
    )
    run_path = write_run_evidence(
        RunResult(
            run_id=run_spec.run_id,
            status=RunStatus.SUCCESS,
            run_spec=run_spec,
            provenance_info={"execution_metadata": "legacy non-JSON value"},
        ),
        output_dir=tmp_path,
    )
    record = json.loads(run_path.read_text(encoding="utf-8"))
    assert record["observed"]["provenance"]["execution_metadata"] == ("legacy non-JSON value")


def test_checkpoint_false_still_writes_evidence_readable_in_a_fresh_process(
    tmp_path: Path,
) -> None:
    """Evidence persistence must not depend on checkpoint/resume support."""
    study = make_study(tmp_path=tmp_path, study_id="no-checkpoint-evidence")

    def run_condition(run_spec: RunSpec, condition: Condition) -> RunOutput:
        return RunOutput(
            outputs={"run_id": run_spec.run_id, "variant": condition.factor_assignments["variant"]},
            metrics={"primary_outcome": float(condition.factor_assignments["variant"] == "b")},
        )

    results = run_study(
        study,
        checkpoint=False,
        condition_runner=run_condition,
        show_progress=False,
    )

    output_dir = Path(study.output_dir or "")
    records = load_run_evidence_records(output_dir)
    assert len(records) == len(results) == 2
    assert {record["status"] for record in records.values()} == {"success"}
    assert not list((output_dir / "artifacts" / "checkpoints").glob("*.json"))

    project_root = Path(__file__).resolve().parents[1]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(project_root / "src")
    output_literal = json.dumps(str(output_dir))
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; "
                "from design_research_experiments import load_run_evidence_records; "
                f"records = load_run_evidence_records({output_literal}); "
                "print(json.dumps(sorted(record['status'] for record in records.values())))"
            ),
        ],
        cwd=project_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == ["success", "success"]


def test_serial_fail_fast_records_remaining_planned_runs_as_skipped(tmp_path: Path) -> None:
    """Fail-fast should explain every omitted execution with a terminal record."""
    study = make_study(
        tmp_path=tmp_path,
        study_id="serial-fail-fast-evidence",
        run_budget=RunBudget(replicates=1, parallelism=1, fail_fast=True),
    )

    def fail_condition(_run_spec: RunSpec, _condition: Condition) -> RunOutput:
        raise RuntimeError("first run failed")

    results = run_study(study, condition_runner=fail_condition, show_progress=False)
    records = load_run_evidence_records(study.output_dir or tmp_path)

    assert [result.status for result in results] == [RunStatus.FAILED, RunStatus.SKIPPED]
    assert len(records) == 2
    skipped = next(record for record in records.values() if record["status"] == "skipped")
    assert skipped["status_reason"] == "fail_fast_after_failed_run"
    assert skipped["attempted"] is False
    assert skipped["terminal"] is True


def test_parallel_execution_persists_success_and_failure_evidence(tmp_path: Path) -> None:
    """Parallel completion order must not affect per-run evidence persistence."""
    study = make_study(
        tmp_path=tmp_path,
        study_id="parallel-evidence",
        run_budget=RunBudget(replicates=1, parallelism=2, fail_fast=False),
    )

    def mixed_condition(_run_spec: RunSpec, condition: Condition) -> RunOutput:
        if condition.factor_assignments["variant"] == "a":
            raise RuntimeError("expected parallel failure")
        return RunOutput(outputs={"text": "ok"}, metrics={"primary_outcome": 1.0})

    results = run_study(study, condition_runner=mixed_condition, show_progress=False)
    records = load_run_evidence_records(study.output_dir or tmp_path)

    assert {result.status for result in results} == {RunStatus.SUCCESS, RunStatus.FAILED}
    assert {record["status"] for record in records.values()} == {"success", "failed"}
    assert all(record["terminal"] is True for record in records.values())


def test_runner_separates_configured_and_observed_execution_metadata(tmp_path: Path) -> None:
    """Observed adapter metadata should not be rewritten as planned configuration."""
    study = make_study(tmp_path=tmp_path, study_id="metadata-boundary-evidence")

    def metadata_agent(*, problem_packet: object, seed: int) -> dict[str, object]:
        del problem_packet, seed
        return {
            "output": {"text": "ok"},
            "metadata": {
                "model_name": "observed-model",
                "agent_kind": "test-agent",
                "request_id": "request-1",
            },
        }

    results = run_study(
        study,
        agent_bindings={"agent-a": lambda _condition: metadata_agent},
        problem_registry={
            "problem-1": {
                "problem_id": "problem-1",
                "family": "test-problem",
                "brief": "Test problem",
            }
        },
        show_progress=False,
    )
    first_result = results[0]
    assert first_result.run_spec is not None
    assert first_result.run_spec.execution_metadata["model_name"] == "observed-model"
    assert "model_name" not in first_result.configured_execution_metadata
    assert first_result.observed_execution_metadata == {
        "agent_kind": "test-agent",
        "model_name": "observed-model",
        "problem_family": "test-problem",
        "request_id": "request-1",
    }

    record = load_run_evidence_records(study.output_dir or tmp_path)[first_result.run_id]
    assert "model_name" not in record["configured"]["execution_metadata"]
    assert record["observed"]["execution_metadata"]["model_name"] == "observed-model"


def test_parallel_fail_fast_records_cancelled_work_as_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Queued parallel work cancelled by fail-fast should remain fully accounted for."""
    study = make_study(
        tmp_path=tmp_path,
        study_id="parallel-fail-fast-evidence",
        factors=(
            Factor(
                name="variant",
                description="Parallel cancellation variant",
                kind=FactorKind.MANIPULATED,
                levels=tuple(Level(name=str(index), value=index) for index in range(10)),
            ),
        ),
        run_budget=RunBudget(replicates=1, parallelism=2, fail_fast=True),
    )
    other_worker_started = threading.Event()
    release_workers = threading.Event()
    original_skipped_result = runner_module._skipped_run_result

    def record_cancellation(run_spec: RunSpec, *, reason: str) -> RunResult:
        result = original_skipped_result(run_spec, reason=reason)
        release_workers.set()
        return result

    monkeypatch.setattr(runner_module, "_skipped_run_result", record_cancellation)

    def controlled_condition(_run_spec: RunSpec, condition: Condition) -> RunOutput:
        if condition.factor_assignments["variant"] == 0:
            assert other_worker_started.wait(timeout=1)
            raise RuntimeError("trigger fail-fast")
        other_worker_started.set()
        assert release_workers.wait(timeout=1)
        return RunOutput(outputs={"text": "completed after cancellation"})

    try:
        results = run_study(study, condition_runner=controlled_condition, show_progress=False)
    finally:
        release_workers.set()

    records = load_run_evidence_records(study.output_dir or tmp_path)
    assert len(results) == len(records) == 10
    assert RunStatus.FAILED in {result.status for result in results}
    assert RunStatus.SKIPPED in {result.status for result in results}
    skipped_records = [record for record in records.values() if record["status"] == "skipped"]
    assert skipped_records
    assert all(
        record["status_reason"] == "cancelled_after_failed_run" for record in skipped_records
    )
    assert all(record["terminal"] is True for record in records.values())


def test_abnormal_interruption_leaves_honest_running_and_pending_records(tmp_path: Path) -> None:
    """An unhandled interruption should remain visible instead of erasing planned work."""
    study = make_study(tmp_path=tmp_path, study_id="interrupted-evidence")

    def interrupt_condition(_run_spec: RunSpec, _condition: Condition) -> RunOutput:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_study(study, condition_runner=interrupt_condition, show_progress=False)

    records = load_run_evidence_records(study.output_dir or tmp_path)
    assert len(records) == 2
    assert sorted(record["status"] for record in records.values()) == ["pending", "running"]
    assert all(record["terminal"] is False for record in records.values())


def test_terminal_evidence_survives_directory_export_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Per-run evidence should precede the final canonical directory export."""
    study = make_study(tmp_path=tmp_path, study_id="export-failure-evidence")

    def run_condition(_run_spec: RunSpec, _condition: Condition) -> RunOutput:
        return RunOutput(outputs={"text": "ok"}, metrics={"primary_outcome": 1.0})

    def fail_export(**_kwargs: object) -> dict[str, Path]:
        raise RuntimeError("directory export failed")

    monkeypatch.setattr(runner_module, "export_canonical_artifacts", fail_export)
    with pytest.raises(RuntimeError, match="directory export failed"):
        run_study(
            study,
            checkpoint=False,
            condition_runner=run_condition,
            show_progress=False,
        )

    records = load_run_evidence_records(study.output_dir or tmp_path)
    assert len(records) == 2
    assert all(record["status"] == "success" for record in records.values())
    assert all(record["terminal"] is True for record in records.values())
