"""Tests for study validation and serial runner behavior."""

from __future__ import annotations

from pathlib import Path

from design_research_experiments.conditions import Factor, FactorKind, Level
from design_research_experiments.hypotheses import AnalysisPlan, Hypothesis, OutcomeSpec
from design_research_experiments.runners import run_study
from design_research_experiments.study import RunBudget, SeedPolicy, Study, validate_study


def test_validate_study_detects_unknown_hypothesis_dependent_variable() -> None:
    """Validation should fail when a hypothesis references an unknown outcome."""
    study = Study(
        study_id="validation-study",
        title="Validation Study",
        description="validation",
        factors=(
            Factor(
                name="agent_kind",
                description="Agent",
                kind=FactorKind.MANIPULATED,
                levels=(Level(name="a", value="a"),),
            ),
        ),
        outcomes=(
            OutcomeSpec(
                name="defined_outcome",
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
                statement="invalid dependent var",
                independent_vars=("agent_kind",),
                dependent_vars=("missing_outcome",),
                linked_analysis_plan_id="ap1",
            ),
        ),
        analysis_plans=(
            AnalysisPlan(analysis_plan_id="ap1", hypothesis_ids=("h1",), tests=("ttest",)),
        ),
        problem_ids=("problem-1",),
    )

    errors = validate_study(study)

    assert any("missing_outcome" in error for error in errors)


def test_run_study_executes_serial_with_callable_agent(tmp_path: Path) -> None:
    """Serial runner should execute and export one run with callable agents."""

    def baseline_agent(*, problem_packet: object, seed: int) -> dict[str, object]:
        """Return deterministic mock output."""
        del problem_packet
        return {
            "output": {"text": f"seed={seed}"},
            "metrics": {"input_tokens": 5, "output_tokens": 7, "cost_usd": 0.01},
            "events": [
                {
                    "event_type": "assistant_output",
                    "text": "mock response",
                    "actor_id": "agent",
                }
            ],
            "metadata": {"model_name": "mock-model"},
        }

    study = Study(
        study_id="run-study",
        title="Run Study",
        description="runner",
        factors=(
            Factor(
                name="difficulty",
                description="Difficulty",
                kind=FactorKind.MANIPULATED,
                levels=(Level(name="low", value="low"),),
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
                statement="runner hypothesis",
                independent_vars=("difficulty",),
                dependent_vars=("primary_outcome",),
                linked_analysis_plan_id="ap1",
            ),
        ),
        analysis_plans=(
            AnalysisPlan(analysis_plan_id="ap1", hypothesis_ids=("h1",), tests=("ttest",)),
        ),
        run_budget=RunBudget(replicates=1, parallelism=1),
        seed_policy=SeedPolicy(base_seed=42),
        output_dir=tmp_path,
        problem_ids=("problem-1",),
        agent_specs=("baseline",),
    )

    results = run_study(
        study,
        agent_bindings={"baseline": baseline_agent},
        dry_run=False,
    )

    assert len(results) == 1
    assert results[0].status.value == "success"
    assert (tmp_path / "runs.csv").exists()
