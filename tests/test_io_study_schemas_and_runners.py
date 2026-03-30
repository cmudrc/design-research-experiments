"""Tests for IO, schema utilities, study serialization, and runner edge paths."""

from __future__ import annotations

import csv
import importlib
import json
import random
import sqlite3
import sys
import types
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from design_research_experiments import runners as runner_module
from design_research_experiments.artifacts import (
    bundle_results,
    canonical_artifact_paths,
    checkpoint_run_result,
    export_canonical_artifacts,
    initialize_artifact_layout,
    load_checkpointed_run_results,
)
from design_research_experiments.conditions import Condition, Factor, FactorKind, Level
from design_research_experiments.io import csv_io, json_io, sqlite_io, yaml_io
from design_research_experiments.runners import (
    dry_run_validate,
    reproducible_seed,
    resume_study,
    run_study,
)
from design_research_experiments.schemas import (
    Observation,
    ObservationLevel,
    ProvenanceMetadata,
    RunBudget,
    RunStatus,
    SeedPolicy,
    hash_identifier,
    load_callable,
    resolve_git_sha,
    stable_json_dumps,
    to_jsonable,
)
from design_research_experiments.study import RunResult, RunSpec, Study, load_study, validate_study

from .helpers import make_study


@dataclass(slots=True)
class _DataclassPayload:
    """Small dataclass for to_jsonable conversion tests."""

    value: int


@dataclass(slots=True)
class _RecordedProgress:
    """Fake progress adapter used to capture runner updates in tests."""

    study_id: str
    total: int
    initial: int
    pending_runs: int
    show_progress: bool | None
    existing_statuses: tuple[RunStatus, ...]
    success: int
    failed: int
    recorded_statuses: list[RunStatus]
    closed: bool = False

    def record_result(self, result: RunResult) -> None:
        """Track one completed result update."""
        self.recorded_statuses.append(result.status)
        if result.status == RunStatus.SUCCESS:
            self.success += 1
        elif result.status == RunStatus.FAILED:
            self.failed += 1

    def close(self) -> None:
        """Record close calls from the runner."""
        self.closed = True


def _agent_success(*, problem_packet: object, seed: int) -> dict[str, object]:
    """Return deterministic successful output."""
    del problem_packet
    return {
        "output": {"text": f"ok-{seed}"},
        "metrics": {"input_tokens": 1, "output_tokens": 2, "cost_usd": 0.001},
        "events": [{"event_type": "assistant_output", "text": "ok", "actor_id": "agent"}],
    }


def _agent_failure(*, problem_packet: object, seed: int) -> dict[str, object]:
    """Raise to trigger isolated run failure."""
    del problem_packet, seed
    raise RuntimeError("boom")


def _record_progress_factory(
    created: list[_RecordedProgress],
):
    """Build a fake progress factory that records one adapter per call."""

    def _factory(
        *,
        study_id: str,
        total: int,
        initial: int,
        run_results: list[RunResult],
        pending_runs: int,
        show_progress: bool | None,
    ) -> _RecordedProgress:
        progress = _RecordedProgress(
            study_id=study_id,
            total=total,
            initial=initial,
            pending_runs=pending_runs,
            show_progress=show_progress,
            existing_statuses=tuple(result.status for result in run_results),
            success=sum(1 for result in run_results if result.status == RunStatus.SUCCESS),
            failed=sum(1 for result in run_results if result.status == RunStatus.FAILED),
            recorded_statuses=[],
        )
        created.append(progress)
        return progress

    return _factory


@dataclass(slots=True)
class _FakeTqdmBar:
    """Minimal tqdm-compatible spy used for adapter tests."""

    postfixes: list[dict[str, int]]
    updates: list[int]
    closed: bool = False

    def update(self, steps: int = 1) -> None:
        """Record one update call."""
        self.updates.append(steps)

    def set_postfix(
        self,
        ordered_dict: Mapping[str, int] | None = None,
        *,
        refresh: bool = True,
    ) -> None:
        """Record postfix payloads."""
        del refresh
        self.postfixes.append(dict(ordered_dict or {}))

    def close(self) -> None:
        """Record close calls."""
        self.closed = True


@dataclass(slots=True)
class _FakeStream:
    """Simple stderr stub with configurable TTY behavior."""

    tty: bool

    def isatty(self) -> bool:
        """Return the configured TTY state."""
        return self.tty


def test_io_modules_yaml_json_csv_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """IO helpers should read/write canonical file formats and error when YAML missing."""
    rows = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    csv_path = tmp_path / "table.csv"
    csv_io.write_csv(csv_path, rows)
    read_rows = csv_io.read_csv(csv_path)
    assert len(read_rows) == 2

    json_path = tmp_path / "payload.json"
    json_io.write_json(json_path, {"k": [1, 2]})
    assert json_io.read_json(json_path)["k"] == [1, 2]

    yaml_path = tmp_path / "payload.yaml"
    yaml_io.write_yaml(yaml_path, {"k": "v"})
    assert yaml_io.read_yaml(yaml_path)["k"] == "v"

    sqlite_path = tmp_path / "tables.sqlite"
    sqlite_io.mirror_tables_to_sqlite(sqlite_path, tables={"rows": rows, "empty": []})
    with sqlite3.connect(sqlite_path) as connection:
        result = list(connection.execute("SELECT a, b FROM rows ORDER BY a"))
    assert result == [("1", "x"), ("2", "y")]

    monkeypatch.setattr(yaml_io, "yaml", None)
    with pytest.raises(RuntimeError):
        yaml_io.write_yaml(tmp_path / "bad.yaml", {"k": "v"})
    with pytest.raises(RuntimeError):
        yaml_io.read_yaml(yaml_path)


def test_schema_utilities_and_callable_loading(tmp_path: Path) -> None:
    """Schema utility functions should serialize deterministically and validate callables."""
    seed_policy = SeedPolicy(base_seed=1)
    assert seed_policy.derive_seed("s", "c", 1) == seed_policy.derive_seed("s", "c", 1)

    with pytest.raises(ValueError):
        RunBudget(replicates=0)

    observation = Observation(
        timestamp="2026-01-01T00:00:00+00:00",
        record_id="evt-1",
        text="hello",
        session_id="session",
        actor_id="actor",
        event_type="assistant_output",
        meta_json={"x": 1},
        level=ObservationLevel.STEP,
    )
    assert observation.to_row()["meta_json"].startswith("{")

    provenance = ProvenanceMetadata.capture(package_names=("not-installed-package",), cwd=tmp_path)
    assert provenance.package_versions["not-installed-package"] == "not-installed"

    payload = {
        "enum": RunStatus.SUCCESS,
        "path": Path("x/y"),
        "set": {"a", "b"},
        "dc": _DataclassPayload(1),
    }
    serialized = to_jsonable(payload)
    assert serialized["enum"] == "success"
    assert isinstance(stable_json_dumps(serialized), str)
    assert hash_identifier("id", {"a": 1}).startswith("id-")

    module = types.ModuleType("fake_callable_module")

    def _callable() -> str:
        """Small callable for load_callable tests."""
        return "ok"

    module.callable_fn = _callable
    module.not_callable = 1
    sys.modules[module.__name__] = module

    loaded = load_callable("fake_callable_module:callable_fn")
    assert loaded() == "ok"

    with pytest.raises(ValueError):
        load_callable("missingcolon")

    with pytest.raises(ValueError):
        load_callable("fake_callable_module:not_callable")

    assert resolve_git_sha(cwd=tmp_path / "missing") is None


def test_study_serialization_validation_and_loading(tmp_path: Path) -> None:
    """Study serialization and validation should support YAML/JSON round trips."""
    study = make_study(tmp_path=tmp_path, study_id="serialization-study")

    yaml_path = tmp_path / "study.yaml"
    json_path = tmp_path / "study.json"
    study.to_yaml(yaml_path)
    study.to_json(json_path)

    loaded_yaml = Study.from_yaml(yaml_path)
    loaded_json = Study.from_json(json_path)
    assert loaded_yaml.study_id == study.study_id
    assert loaded_json.study_id == study.study_id
    assert loaded_yaml.to_dict()["schema_version"] == study.to_dict()["schema_version"]
    assert loaded_json.to_dict()["schema_version"] == study.to_dict()["schema_version"]

    from_dict = Study.from_dict(study.to_dict())
    assert from_dict.study_id == study.study_id
    assert study.to_dict()["schema_version"]

    assert load_study(yaml_path).study_id == study.study_id
    assert load_study(json_path).study_id == study.study_id

    with pytest.raises(ValueError):
        load_study(tmp_path / "study.txt")

    broken = make_study(tmp_path=tmp_path, study_id="broken", problem_ids=())
    broken.primary_outcomes = ("missing",)
    errors = validate_study(broken)
    assert errors


def test_artifact_checkpoint_bundle_and_runner_paths(tmp_path: Path) -> None:
    """Artifacts and runners should support checkpoint, resume, dry-run, and failures."""
    study = make_study(
        tmp_path=tmp_path,
        study_id="runner-study",
        run_budget=RunBudget(replicates=1, parallelism=2, fail_fast=False),
    )

    # Dry-run path
    assert run_study(study, dry_run=True) == []

    # Parallel run path
    results = run_study(
        study,
        parallelism=2,
        agent_bindings={"agent-a": lambda _condition: _agent_success},
        checkpoint=True,
        include_sqlite=True,
    )
    assert results

    # Resume path should load checkpoints and preserve count.
    resumed = resume_study(
        study,
        agent_bindings={"agent-a": lambda _condition: _agent_success},
    )
    assert len(resumed) == len(results)

    loaded = load_checkpointed_run_results(study.output_dir or tmp_path / "runner-study")
    assert loaded

    # Failure + fail-fast path
    failing_study = make_study(
        tmp_path=tmp_path,
        study_id="failing-study",
        run_budget=RunBudget(replicates=1, parallelism=1, fail_fast=True),
    )
    failing_results = run_study(
        failing_study,
        agent_bindings={"agent-a": lambda _condition: _agent_failure},
        checkpoint=False,
    )
    assert len(failing_results) == 1
    assert failing_results[0].status == RunStatus.FAILED

    # Validation helper paths
    inadmissible = Condition("cond-x", {"variant": "a"}, {}, admissible=False)
    report = dry_run_validate(study, conditions=[inadmissible])
    assert report.errors

    with pytest.raises(ValueError):
        run_study(study, parallelism=0)

    # Reproducible-seed context should restore random state.
    random.seed(99)
    before = random.random()
    with reproducible_seed(42):
        _ = random.random()
    after = random.random()
    random.seed(99)
    _ = random.random()  # consume first
    expected_after = random.random()
    assert abs(after - expected_after) < 1e-9
    assert before != after

    # Explicit artifact export branches with mapping observations and missing run_spec.
    output_dir = tmp_path / "artifact-extra"
    paths = canonical_artifact_paths(output_dir)
    initialized = initialize_artifact_layout(output_dir)
    assert initialized.output_dir == paths.output_dir

    run_with_mapping_obs = RunResult(
        run_id="run-map",
        status=RunStatus.SUCCESS,
        observations=[{"meta_json": {"k": 1}}],
        evaluator_outputs=[{"metric_name": "score", "metric_value": 1.0}],
        run_spec=None,
    )
    exported = export_canonical_artifacts(
        study=study,
        conditions=[Condition("cond-1", {"variant": "a"}, {})],
        run_results=[run_with_mapping_obs],
        output_dir=output_dir,
        include_sqlite=True,
    )
    assert exported["events.csv"].exists()

    # Checkpoint load when directory absent.
    assert load_checkpointed_run_results(tmp_path / "missing-output") == {}

    run_spec = RunSpec(
        run_id="run-checkpoint",
        study_id="s",
        condition_id="c",
        problem_id="p",
        replicate=1,
        seed=1,
        agent_spec_ref="a",
        problem_spec_ref="p",
    )
    checkpointed = RunResult(run_id="run-checkpoint", status=RunStatus.SUCCESS, run_spec=run_spec)
    checkpoint_path = checkpoint_run_result(checkpointed, output_dir=output_dir)
    assert checkpoint_path.exists()

    bundle_path = bundle_results(output_dir)
    assert bundle_path.exists()

    with (output_dir / "events.csv").open("r", encoding="utf-8", newline="") as file_obj:
        header = next(csv.reader(file_obj))
    assert "meta_json" in header

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["study_id"] == study.study_id


def test_run_study_reports_serial_progress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Serial runs should report progress through the shared adapter."""
    created: list[_RecordedProgress] = []
    monkeypatch.setattr(
        runner_module,
        "_create_run_progress",
        _record_progress_factory(created),
    )
    study = make_study(
        tmp_path=tmp_path,
        study_id="serial-progress-study",
        run_budget=RunBudget(replicates=1, parallelism=1),
    )

    results = run_study(
        study,
        parallelism=1,
        agent_bindings={"agent-a": lambda _condition: _agent_success},
        show_progress=True,
    )

    assert len(created) == 1
    progress = created[0]
    assert progress.study_id == study.study_id
    assert progress.total == len(results)
    assert progress.initial == 0
    assert progress.pending_runs == len(results)
    assert progress.show_progress is True
    assert progress.recorded_statuses == [RunStatus.SUCCESS] * len(results)
    assert progress.success == len(results)
    assert progress.failed == 0
    assert progress.closed is True


def test_run_study_reports_parallel_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parallel runs should update the shared adapter as futures complete."""
    created: list[_RecordedProgress] = []
    monkeypatch.setattr(
        runner_module,
        "_create_run_progress",
        _record_progress_factory(created),
    )
    study = make_study(
        tmp_path=tmp_path,
        study_id="parallel-progress-study",
        run_budget=RunBudget(replicates=1, parallelism=2),
    )

    results = run_study(
        study,
        parallelism=2,
        agent_bindings={"agent-a": lambda _condition: _agent_success},
        show_progress=True,
    )

    assert len(created) == 1
    progress = created[0]
    assert progress.total == len(results)
    assert progress.pending_runs == len(results)
    assert len(progress.recorded_statuses) == len(results)
    assert all(status == RunStatus.SUCCESS for status in progress.recorded_statuses)
    assert progress.success == len(results)
    assert progress.failed == 0
    assert progress.closed is True


def test_resume_study_progress_tracks_completed_and_pending_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume should seed progress from checkpointed results and advance only pending runs."""
    created: list[_RecordedProgress] = []
    monkeypatch.setattr(
        runner_module,
        "_create_run_progress",
        _record_progress_factory(created),
    )
    study = make_study(
        tmp_path=tmp_path,
        study_id="resume-progress-study",
        run_budget=RunBudget(replicates=1, parallelism=1),
    )
    conditions = runner_module.build_design(study)
    run_spec = runner_module._build_run_specs(study=study, conditions=conditions)[0]
    checkpoint_run_result(
        RunResult(run_id=run_spec.run_id, status=RunStatus.SUCCESS, run_spec=run_spec),
        output_dir=study.output_dir or tmp_path / study.study_id,
    )

    results = resume_study(
        study,
        parallelism=1,
        agent_bindings={"agent-a": lambda _condition: _agent_success},
        show_progress=True,
    )

    assert len(created) == 1
    progress = created[0]
    assert progress.total == len(results)
    assert progress.initial == 1
    assert progress.pending_runs == len(results) - 1
    assert progress.existing_statuses == (RunStatus.SUCCESS,)
    assert progress.recorded_statuses == [RunStatus.SUCCESS]
    assert progress.success == len(results)
    assert progress.failed == 0
    assert progress.closed is True


def test_resume_study_with_no_pending_runs_still_closes_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume should pass a zero-pending state through the progress adapter."""
    study = make_study(
        tmp_path=tmp_path,
        study_id="resume-complete-study",
        run_budget=RunBudget(replicates=1, parallelism=1),
    )
    run_study(
        study,
        parallelism=1,
        agent_bindings={"agent-a": lambda _condition: _agent_success},
        checkpoint=True,
        show_progress=False,
    )

    created: list[_RecordedProgress] = []
    monkeypatch.setattr(
        runner_module,
        "_create_run_progress",
        _record_progress_factory(created),
    )

    results = resume_study(
        study,
        parallelism=1,
        agent_bindings={"agent-a": lambda _condition: _agent_success},
        show_progress=True,
    )

    assert len(created) == 1
    progress = created[0]
    assert progress.total == len(results)
    assert progress.initial == len(results)
    assert progress.pending_runs == 0
    assert progress.recorded_statuses == []
    assert progress.success == len(results)
    assert progress.failed == 0
    assert progress.closed is True


def test_run_study_dry_run_skips_progress_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dry-run validation should not create a progress adapter."""
    study = make_study(tmp_path=tmp_path, study_id="dry-run-progress-study")

    def _fail(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("progress should not be created for dry-run")

    monkeypatch.setattr(runner_module, "_create_run_progress", _fail)

    assert run_study(study, dry_run=True, show_progress=True) == []


def test_create_run_progress_respects_suppression_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Progress adapter should avoid visible bars when disabled or not interactive."""
    monkeypatch.setattr(
        runner_module,
        "tqdm",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("tqdm should not be created")),
    )

    disabled = runner_module._create_run_progress(
        study_id="suppressed-study",
        total=2,
        initial=0,
        run_results=[],
        pending_runs=2,
        show_progress=False,
    )
    assert isinstance(disabled._bar, runner_module._NoOpProgressBar)

    monkeypatch.setattr(runner_module.sys, "stderr", _FakeStream(tty=False))
    auto_disabled = runner_module._create_run_progress(
        study_id="suppressed-study",
        total=2,
        initial=0,
        run_results=[],
        pending_runs=2,
        show_progress=None,
    )
    assert isinstance(auto_disabled._bar, runner_module._NoOpProgressBar)

    zero_pending = runner_module._create_run_progress(
        study_id="suppressed-study",
        total=2,
        initial=2,
        run_results=[],
        pending_runs=0,
        show_progress=True,
    )
    assert isinstance(zero_pending._bar, runner_module._NoOpProgressBar)


def test_create_run_progress_uses_tqdm_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Visible progress should configure the tqdm adapter with the expected defaults."""
    calls: list[dict[str, Any]] = []
    bar = _FakeTqdmBar(postfixes=[], updates=[])

    def _fake_tqdm(**kwargs: Any) -> _FakeTqdmBar:
        calls.append(kwargs)
        return bar

    monkeypatch.setattr(runner_module, "tqdm", _fake_tqdm)
    monkeypatch.setattr(runner_module.sys, "stderr", _FakeStream(tty=True))

    progress = runner_module._create_run_progress(
        study_id="visible-study",
        total=3,
        initial=1,
        run_results=[RunResult(run_id="existing", status=RunStatus.SUCCESS)],
        pending_runs=2,
        show_progress=None,
    )
    progress.record_result(RunResult(run_id="new", status=RunStatus.FAILED))
    progress.close()

    assert len(calls) == 1
    assert calls[0]["total"] == 3
    assert calls[0]["initial"] == 1
    assert calls[0]["desc"] == "visible-study"
    assert calls[0]["unit"] == "run"
    assert calls[0]["dynamic_ncols"] is True
    assert calls[0]["leave"] is True
    assert calls[0]["file"] is runner_module.sys.stderr
    assert bar.updates == [1]
    assert bar.postfixes == [{"success": 1, "failed": 0}, {"success": 1, "failed": 1}]
    assert bar.closed is True


def test_dry_run_validate_reports_tight_max_run_budget(tmp_path: Path) -> None:
    """Dry-run validation should surface a study run budget that is too small."""
    study = make_study(
        tmp_path=tmp_path,
        study_id="max-run-budget-study",
        problem_ids=("problem-1", "problem-2"),
        agent_specs=("agent-a", "agent-b"),
        run_budget=RunBudget(replicates=2, parallelism=1, max_runs=3),
    )

    report = dry_run_validate(study, conditions=runner_module.build_design(study))

    assert any("Run budget max_runs is below" in error for error in report.errors)


def test_reproducible_seed_restores_fake_numpy_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reproducible seed should restore optional numpy state after the context exits."""

    class _FakeNumpyRandom:
        """Minimal numpy.random-compatible stub."""

        def __init__(self) -> None:
            self.state: tuple[str, int] = ("initial", 0)

        def get_state(self) -> tuple[str, int]:
            """Return the current fake RNG state."""
            return self.state

        def set_state(self, state: tuple[str, int]) -> None:
            """Restore the saved fake RNG state."""
            self.state = state

        def seed(self, seed: int) -> None:
            """Record the seeded state."""
            self.state = ("seeded", seed)

    fake_numpy = types.SimpleNamespace(random=_FakeNumpyRandom())

    def fake_import(name: str) -> Any:
        """Provide a fake numpy module while preserving other imports."""
        if name == "numpy":
            return fake_numpy
        return importlib.import_module(name)

    monkeypatch.setattr(runner_module.importlib, "import_module", fake_import)

    with reproducible_seed(13):
        assert fake_numpy.random.state == ("seeded", 13)

    assert fake_numpy.random.state == ("initial", 0)


def test_build_run_specs_resolves_alias_and_default_ids(tmp_path: Path) -> None:
    """Run-spec construction should honor alias keys and default fallback IDs."""
    aliased_study = make_study(tmp_path=tmp_path, study_id="alias-study")
    aliased_condition = Condition(
        "cond-alias",
        {"variant": "a", "agent": "agent-alias", "problem": "problem-alias"},
        {},
    )
    aliased_specs = runner_module._build_run_specs(aliased_study, [aliased_condition])
    assert aliased_specs[0].agent_spec_ref == "agent-alias"
    assert aliased_specs[0].problem_spec_ref == "problem-alias"

    default_study = make_study(
        tmp_path=tmp_path,
        study_id="default-study",
        problem_ids=(),
        agent_specs=(),
    )
    default_condition = Condition("cond-default", {"variant": "a"}, {})
    default_specs = runner_module._build_run_specs(default_study, [default_condition])
    assert default_specs[0].agent_spec_ref == "default-agent"
    assert default_specs[0].problem_spec_ref == "default-problem"


def test_build_run_specs_does_not_expand_agent_bound_comparisons(tmp_path: Path) -> None:
    """Agent-bound comparison factors should not cross with top-level agent specs."""
    study = make_study(
        tmp_path=tmp_path,
        study_id="agent-bound-comparison",
        factors=(
            Factor(
                name="agent_id",
                description="Agent strategy",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="agent_a", value="agent-a"),
                    Level(name="agent_b", value="agent-b"),
                ),
            ),
        ),
        problem_ids=("problem-1", "problem-2"),
        agent_specs=("fallback-a", "fallback-b"),
    )

    specs = runner_module._build_run_specs(study, runner_module.build_design(study))

    assert len(specs) == 4
    assert {spec.agent_spec_ref for spec in specs} == {"agent-a", "agent-b"}
    assert {spec.problem_spec_ref for spec in specs} == {"problem-1", "problem-2"}


def test_build_run_specs_does_not_expand_problem_bound_comparisons(tmp_path: Path) -> None:
    """Problem-bound comparison factors should not cross with top-level problem IDs."""
    study = make_study(
        tmp_path=tmp_path,
        study_id="problem-bound-comparison",
        factors=(
            Factor(
                name="problem_id",
                description="Problem arm",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="problem_a", value="problem-a"),
                    Level(name="problem_b", value="problem-b"),
                ),
            ),
        ),
        problem_ids=("fallback-problem-a", "fallback-problem-b"),
        agent_specs=("agent-a", "agent-b"),
    )

    specs = runner_module._build_run_specs(study, runner_module.build_design(study))

    assert len(specs) == 4
    assert {spec.agent_spec_ref for spec in specs} == {"agent-a", "agent-b"}
    assert {spec.problem_spec_ref for spec in specs} == {"problem-a", "problem-b"}
