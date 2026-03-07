"""Minimal example usage for design-research-experiments."""

from __future__ import annotations

from design_research_experiments.conditions import Factor, FactorKind, Level
from design_research_experiments.hypotheses import AnalysisPlan, Hypothesis, OutcomeSpec
from design_research_experiments.study import Study


def main() -> None:
    """Construct and print a tiny study definition."""
    study = Study(
        study_id="example-study",
        title="Example Study",
        description="Minimal study object for notebook/script usage.",
        factors=(
            Factor(
                name="prompt_frame",
                description="Prompt framing",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="neutral", value="neutral"),
                    Level(name="challenge", value="challenge"),
                ),
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
                label="Prompt framing effect",
                statement="Prompt frame influences the primary outcome.",
                independent_vars=("prompt_frame",),
                dependent_vars=("primary_outcome",),
                linked_analysis_plan_id="ap1",
            ),
        ),
        analysis_plans=(
            AnalysisPlan(analysis_plan_id="ap1", hypothesis_ids=("h1",), tests=("ttest",)),
        ),
        problem_ids=("problem-1",),
    )

    print(study.to_dict())


if __name__ == "__main__":
    main()
