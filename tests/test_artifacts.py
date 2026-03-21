"""Tests for canonical artifact export."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from design_research_experiments.artifacts import export_canonical_artifacts
from design_research_experiments.conditions import Condition, Factor, FactorKind, Level
from design_research_experiments.designs import build_design
from design_research_experiments.hypotheses import AnalysisPlan, Hypothesis, OutcomeSpec
from design_research_experiments.recipes import build_strategy_comparison_study
from design_research_experiments.schemas import Observation, ObservationLevel, RunStatus
from design_research_experiments.study import RunResult, RunSpec, Study


def test_export_canonical_artifacts_writes_required_files_and_columns(tmp_path: Path) -> None:
    """Artifact export should emit all canonical files with required table columns."""
    study = Study(
        study_id="artifact-study",
        title="Artifact Study",
        description="artifact export test",
        factors=(
            Factor(
                name="agent_kind",
                description="Agent",
                kind=FactorKind.MANIPULATED,
                levels=(Level(name="baseline", value="baseline"),),
            ),
        ),
        outcomes=(
            OutcomeSpec(
                name="primary_outcome",
                source_table="runs",
                column="primary_outcome",
                aggregation="mean",
                primary=True,
            ),
        ),
        hypotheses=(
            Hypothesis(
                hypothesis_id="h1",
                label="H1",
                statement="artifact hypothesis",
                independent_vars=("agent_kind",),
                dependent_vars=("primary_outcome",),
                linked_analysis_plan_id="ap1",
            ),
        ),
        analysis_plans=(
            AnalysisPlan(analysis_plan_id="ap1", hypothesis_ids=("h1",), tests=("ttest",)),
        ),
        output_dir=tmp_path,
        problem_ids=("problem-1",),
    )

    condition = Condition(
        condition_id="cond-1",
        factor_assignments={"agent_kind": "baseline"},
        block_assignments={},
        admissible=True,
    )

    run_spec = RunSpec(
        run_id="run-1",
        study_id=study.study_id,
        condition_id=condition.condition_id,
        problem_id="problem-1",
        replicate=1,
        seed=123,
        agent_spec_ref="baseline-agent",
        problem_spec_ref="problem-1",
        execution_metadata={
            "problem_family": "ideation",
            "agent_id": "baseline-agent",
            "agent_kind": "baseline",
            "pattern_name": "single-step",
            "model_name": "test-model",
        },
    )

    observation = Observation(
        timestamp="2026-01-01T00:00:00+00:00",
        record_id="evt-1",
        text="hello",
        session_id="run-1",
        actor_id="agent",
        event_type="assistant_output",
        meta_json={"token": 1},
        level=ObservationLevel.STEP,
        study_id=study.study_id,
        run_id="run-1",
        condition_id=condition.condition_id,
    )

    run_result = RunResult(
        run_id="run-1",
        status=RunStatus.SUCCESS,
        outputs={"text": "hello"},
        metrics={
            "input_tokens": 10,
            "output_tokens": 20,
            "primary_outcome": 0.75,
        },
        evaluator_outputs=[
            {
                "evaluator_id": "eval",
                "metric_name": "score",
                "metric_value": 0.75,
                "metric_unit": "unitless",
                "aggregation_level": "run",
                "notes_json": {"ok": True},
            }
        ],
        cost=0.02,
        latency=1.25,
        trace_refs=["artifacts/traces/run-1.json"],
        run_spec=run_spec,
        observations=[observation],
        started_at="2026-01-01T00:00:00+00:00",
        ended_at="2026-01-01T00:00:01+00:00",
    )

    paths = export_canonical_artifacts(
        study=study,
        conditions=[condition],
        run_results=[run_result],
        output_dir=tmp_path,
    )

    expected_names = {
        "study.yaml",
        "manifest.json",
        "conditions.csv",
        "runs.csv",
        "events.csv",
        "evaluations.csv",
        "hypotheses.json",
        "analysis_plan.json",
        "artifacts",
    }
    assert set(paths) == expected_names
    assert all(path.exists() for path in paths.values())

    events_header = (tmp_path / "events.csv").read_text(encoding="utf-8").splitlines()[0]
    for required_column in [
        "timestamp",
        "record_id",
        "text",
        "session_id",
        "actor_id",
        "event_type",
        "meta_json",
    ]:
        assert required_column in events_header


def test_exported_condition_rows_include_comparison_metadata(tmp_path: Path) -> None:
    """Comparison studies should export labels and baseline metadata in assignment metadata."""
    study = build_strategy_comparison_study()
    study.output_dir = tmp_path
    conditions = build_design(study)

    export_canonical_artifacts(
        study=study,
        conditions=conditions,
        run_results=[],
        output_dir=tmp_path,
    )

    with (tmp_path / "conditions.csv").open("r", encoding="utf-8", newline="") as file_obj:
        rows = list(csv.DictReader(file_obj))

    assert rows
    assignment_meta = json.loads(rows[0]["assignment_meta_json"])
    assert "condition_label" in assignment_meta
    assert "comparison_axes" in assignment_meta
    assert "comparison_baseline" in assignment_meta
    assert "agent_id" in assignment_meta["comparison_axes"]
