"""Minimal study-construction example.

## Introduction
Construct the smallest useful ``Study`` using only top-level ``drex`` exports.

## Technical Implementation
1. Define one manipulated factor with two levels.
2. Register one primary outcome plus one hypothesis and analysis plan.
3. Print ``study.to_dict()`` so the serialized schema is visible in one place.

## Expected Results
The script prints one dictionary containing study metadata, factor definitions,
hypothesis bindings, and analysis-plan fields.
"""

from __future__ import annotations

import design_research_experiments as drex


def main() -> None:
    """Construct and print a tiny study definition."""
    study = drex.Study(
        study_id="example-study",
        title="Example Study",
        description="Minimal study object for notebook/script usage.",
        factors=(
            drex.Factor(
                name="prompt_frame",
                description="Prompt framing",
                kind=drex.FactorKind.MANIPULATED,
                levels=(
                    drex.Level(name="neutral", value="neutral"),
                    drex.Level(name="challenge", value="challenge"),
                ),
            ),
        ),
        outcomes=(
            drex.OutcomeSpec(
                name="primary_outcome",
                source_table="runs",
                column="primary_outcome",
                aggregation="mean",
                primary=True,
            ),
        ),
        hypotheses=(
            drex.Hypothesis(
                hypothesis_id="h1",
                label="Prompt framing effect",
                statement="Prompt frame influences the primary outcome.",
                independent_vars=("prompt_frame",),
                dependent_vars=("primary_outcome",),
                linked_analysis_plan_id="ap1",
            ),
        ),
        analysis_plans=(
            drex.AnalysisPlan(analysis_plan_id="ap1", hypothesis_ids=("h1",), tests=("ttest",)),
        ),
        problem_ids=("problem-1",),
    )

    print(study.to_dict())


if __name__ == "__main__":
    main()
