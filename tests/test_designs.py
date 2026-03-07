"""Tests for DOE builders."""

from __future__ import annotations

from design_research_experiments.conditions import Factor, FactorKind, Level
from design_research_experiments.designs import build_design
from design_research_experiments.hypotheses import AnalysisPlan, Hypothesis, OutcomeSpec
from design_research_experiments.study import RunBudget, SeedPolicy, Study


def test_build_design_latin_square_assigns_each_treatment_once_per_row_and_column() -> None:
    """Latin square should rotate treatment levels across rows and columns."""
    study = Study(
        study_id="latin-square-study",
        title="Latin Square",
        description="Latin square design check",
        factors=(
            Factor(
                name="row",
                description="Row",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="r1", value="r1"),
                    Level(name="r2", value="r2"),
                    Level(name="r3", value="r3"),
                ),
            ),
            Factor(
                name="column",
                description="Column",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="c1", value="c1"),
                    Level(name="c2", value="c2"),
                    Level(name="c3", value="c3"),
                ),
            ),
            Factor(
                name="treatment",
                description="Treatment",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="a", value="A"),
                    Level(name="b", value="B"),
                    Level(name="c", value="C"),
                ),
            ),
        ),
        design_spec={
            "kind": "latin_square",
            "options": {
                "row_factor": "row",
                "column_factor": "column",
                "treatment_factor": "treatment",
            },
        },
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
                statement="Check latin square",
                independent_vars=("treatment",),
                dependent_vars=("primary_outcome",),
                linked_analysis_plan_id="ap1",
            ),
        ),
        analysis_plans=(
            AnalysisPlan(analysis_plan_id="ap1", hypothesis_ids=("h1",), tests=("anova",)),
        ),
        run_budget=RunBudget(replicates=1),
        seed_policy=SeedPolicy(base_seed=0),
        problem_ids=("problem-1",),
    )

    conditions = build_design(study)

    assert len(conditions) == 9

    by_row: dict[str, set[str]] = {}
    by_column: dict[str, set[str]] = {}
    for condition in conditions:
        row = str(condition.factor_assignments["row"])
        column = str(condition.factor_assignments["column"])
        treatment = str(condition.factor_assignments["treatment"])
        by_row.setdefault(row, set()).add(treatment)
        by_column.setdefault(column, set()).add(treatment)

    assert all(treatments == {"A", "B", "C"} for treatments in by_row.values())
    assert all(treatments == {"A", "B", "C"} for treatments in by_column.values())
