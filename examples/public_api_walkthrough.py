"""Public API walkthrough for design-research-experiments."""

from __future__ import annotations

from pathlib import Path

from design_research_experiments import (
    AnalysisPlan,
    Factor,
    Hypothesis,
    Level,
    OutcomeSpec,
    Study,
    build_design,
    materialize_conditions,
    validate_study,
)


def build_demo_study(output_dir: Path) -> Study:
    """Build a small study covering the core schema objects."""
    return Study(
        study_id="demo-study",
        title="Demo Study",
        description="A tiny study used for local API walkthrough.",
        factors=(
            Factor(
                name="prompt_frame",
                description="Prompt framing style",
                levels=(
                    Level(name="neutral", value="neutral"),
                    Level(name="challenge", value="challenge"),
                ),
            ),
        ),
        hypotheses=(
            Hypothesis(
                hypothesis_id="h1",
                label="Prompt Effect",
                statement="Prompt frame changes primary outcome.",
                independent_vars=("prompt_frame",),
                dependent_vars=("primary_outcome",),
                linked_analysis_plan_id="ap1",
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
        analysis_plans=(AnalysisPlan("ap1", ("h1",), ("ttest",)),),
        output_dir=output_dir,
        problem_ids=("problem-1",),
        agent_specs=("agent-a",),
        primary_outcomes=("primary_outcome",),
    )


def main() -> None:
    """Validate and materialize the demo study."""
    output_dir = Path("artifacts") / "demo-study"
    study = build_demo_study(output_dir)

    errors = validate_study(study)
    if errors:
        raise RuntimeError("\n".join(errors))

    conditions = build_design(study)
    print(f"build_design produced {len(conditions)} conditions")

    direct_conditions = materialize_conditions(study)
    print(f"materialize_conditions produced {len(direct_conditions)} conditions")


if __name__ == "__main__":
    main()
