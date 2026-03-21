"""Tests for IO, schema utilities, study serialization, and runner edge paths."""

from __future__ import annotations

import csv
import importlib
import json
import random
import sqlite3
import sys
import types
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
from design_research_experiments.conditions import Condition
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

    from_dict = Study.from_dict(study.to_dict())
    assert from_dict.study_id == study.study_id

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
        agent_factories={"agent-a": lambda _condition: _agent_success},
        checkpoint=True,
        include_sqlite=True,
    )
    assert results

    # Resume path should load checkpoints and preserve count.
    resumed = resume_study(
        study,
        agent_factories={"agent-a": lambda _condition: _agent_success},
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
        agent_factories={"agent-a": lambda _condition: _agent_failure},
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
