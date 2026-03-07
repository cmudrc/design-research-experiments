"""Public API walkthrough example.

## Introduction
Walk through the core study lifecycle: build, validate, and materialize conditions.

## Technical Implementation
1. Build a compact ``Study`` object with one factor, hypothesis, and outcome.
2. Validate via ``drex.validate_study``.
3. Materialize conditions through both ``drex.build_design`` and
   ``drex.materialize_conditions`` for parity checks.

## Expected Results
The script prints condition counts for both materialization paths and raises an
error only when validation fails.
"""

from __future__ import annotations

from pathlib import Path

import design_research_experiments as drex


def build_demo_study(output_dir: Path) -> drex.Study:
    """Build a small study covering the core schema objects."""
    return drex.Study(
        study_id="demo-study",
        title="Demo Study",
        description="A tiny study used for local API walkthrough.",
        factors=(
            drex.Factor(
                name="prompt_frame",
                description="Prompt framing style",
                levels=(
                    drex.Level(name="neutral", value="neutral"),
                    drex.Level(name="challenge", value="challenge"),
                ),
            ),
        ),
        hypotheses=(
            drex.Hypothesis(
                hypothesis_id="h1",
                label="Prompt Effect",
                statement="Prompt frame changes primary outcome.",
                independent_vars=("prompt_frame",),
                dependent_vars=("primary_outcome",),
                linked_analysis_plan_id="ap1",
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
        analysis_plans=(drex.AnalysisPlan("ap1", ("h1",), ("ttest",)),),
        output_dir=output_dir,
        problem_ids=("problem-1",),
        agent_specs=("agent-a",),
        primary_outcomes=("primary_outcome",),
    )


def main() -> None:
    """Validate and materialize the demo study."""
    output_dir = Path("artifacts") / "demo-study"
    study = build_demo_study(output_dir)

    errors = drex.validate_study(study)
    if errors:
        raise RuntimeError("\n".join(errors))

    conditions = drex.build_design(study)
    print(f"build_design produced {len(conditions)} conditions")

    direct_conditions = drex.materialize_conditions(study)
    print(f"materialize_conditions produced {len(direct_conditions)} conditions")


if __name__ == "__main__":
    main()
