"""Shared test helpers for constructing valid study objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from design_research_experiments.conditions import Constraint, Factor, FactorKind, Level
from design_research_experiments.hypotheses import AnalysisPlan, Hypothesis, OutcomeSpec
from design_research_experiments.study import Block, RunBudget, SeedPolicy, Study


def make_study(
    *,
    tmp_path: Path,
    study_id: str = "test-study",
    design_spec: dict[str, Any] | None = None,
    factors: tuple[Factor, ...] | None = None,
    blocks: tuple[Block, ...] = (),
    constraints: tuple[Constraint, ...] = (),
    problem_ids: tuple[str, ...] = ("problem-1",),
    agent_specs: tuple[str, ...] = ("agent-a",),
    run_budget: RunBudget | None = None,
    seed_policy: SeedPolicy | None = None,
) -> Study:
    """Create a minimal valid study for tests."""
    resolved_factors = factors or (
        Factor(
            name="variant",
            description="Variant",
            kind=FactorKind.MANIPULATED,
            levels=(Level(name="a", value="a"), Level(name="b", value="b")),
        ),
    )

    return Study(
        study_id=study_id,
        title=f"{study_id} title",
        description="test study",
        factors=resolved_factors,
        blocks=blocks,
        constraints=constraints,
        design_spec=design_spec or {"kind": "full_factorial", "randomize": False},
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
                statement="variant changes outcome",
                independent_vars=(resolved_factors[0].name,),
                dependent_vars=("primary_outcome",),
                linked_analysis_plan_id="ap1",
            ),
        ),
        analysis_plans=(
            AnalysisPlan(
                analysis_plan_id="ap1",
                hypothesis_ids=("h1",),
                tests=("ttest",),
                outcomes=("primary_outcome",),
            ),
        ),
        run_budget=run_budget or RunBudget(replicates=1, parallelism=1),
        seed_policy=seed_policy or SeedPolicy(base_seed=123),
        output_dir=tmp_path / study_id,
        problem_ids=problem_ids,
        agent_specs=agent_specs,
        primary_outcomes=("primary_outcome",),
    )
