"""Real-stack interoperability example.

## Introduction
Run one packaged problem from `design-research-problems` through a public
`design-research-agents` baseline and validate the exported `events.csv`
contract with `design-research-analysis`'s artifact-first integration API.

## Technical Implementation
1. Import the package-owned `integration` modules from installed sibling libraries.
2. Execute a one-run study that uses a packaged optimization problem together
   with `SeededRandomBaselineAgent`.
3. Export canonical artifacts and validate the event table through the analysis
   package's artifact-first integration contract.

## Expected Results
The script prints the packaged problem identity, one successful run result, and
the exported artifact filenames after the event table passes validation.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import design_research_experiments as drex


def _load_stack_modules() -> dict[str, object] | None:
    """Import sibling stack packages when the coordinated libraries are installed."""
    try:
        problems_module = importlib.import_module("design_research_problems")
        problems_integration = importlib.import_module("design_research_problems.integration")
        agents_integration = importlib.import_module("design_research_agents.integration")
    except ImportError as exc:
        print(f"Real stack example skipped: {exc}")
        return None

    try:
        analysis_module = importlib.import_module("design_research_analysis")
        analysis_integration = importlib.import_module("design_research_analysis.integration")
    except ImportError as exc:
        print(f"Real stack example skipped: {exc}")
        return None

    return {
        "problems": problems_module,
        "problems_integration": problems_integration,
        "agents_integration": agents_integration,
        "analysis": analysis_module,
        "analysis_integration": analysis_integration,
    }


def main() -> None:
    """Run one real interoperability path across the sibling libraries."""
    modules = _load_stack_modules()
    if modules is None:
        return

    problems_integration = modules["problems_integration"]
    agents_integration = modules["agents_integration"]
    analysis_module = modules["analysis"]
    analysis_integration = modules["analysis_integration"]
    problem_id = "gmpb_default_dynamic_min"
    problem_binding = problems_integration.resolve_problem_binding(problem_id)
    packaged_problem = problem_binding.problem_object

    study = drex.Study(
        study_id="real-stack-interoperability",
        title="Real stack interoperability",
        description="Packaged problem + public agent + validated analysis handoff.",
        output_dir=Path("artifacts") / "real-stack-interoperability",
        problem_ids=(problem_id,),
        agent_specs=("SeededRandomBaselineAgent",),
        outcomes=(
            drex.OutcomeSpec(
                name="primary_outcome",
                source_table="runs",
                column="primary_outcome",
                aggregation="mean",
                primary=True,
            ),
        ),
        run_budget=drex.RunBudget(replicates=1, parallelism=1, max_runs=1),
        primary_outcomes=("primary_outcome",),
    )
    conditions = drex.build_design(study)
    run_results = drex.run_study(
        study,
        conditions=conditions,
        show_progress=False,
    )
    exported_paths = drex.export_analysis_tables(
        study,
        conditions=conditions,
        run_results=run_results,
        output_dir=study.output_dir / "analysis",
        validate_with_analysis_package=True,
    )
    loaded_artifacts = analysis_integration.load_experiment_artifacts(exported_paths["events.csv"])
    report = analysis_integration.validate_experiment_events(exported_paths["events.csv"])
    primary_metric_rows = analysis_module.build_condition_metric_table(
        loaded_artifacts["runs.csv"],
        metric="primary_outcome",
        condition_column="agent_id",
        conditions=loaded_artifacts["conditions.csv"],
        evaluations=loaded_artifacts["evaluations.csv"],
    )
    run_result = run_results[0]

    print("Problem ID:", packaged_problem.metadata.problem_id)
    print("Problem family:", packaged_problem.metadata.kind.value)
    print("Problem integration:", problems_integration.__name__)
    print("Agent integration:", agents_integration.__name__)
    print("Agent:", study.agent_specs[0])
    print("Completed runs:", len(run_results))
    print("Run status:", run_result.status.value)
    print("Output keys:", ", ".join(sorted(run_result.outputs)))
    print("Primary outcome:", run_result.metrics.get("primary_outcome"))
    print("Metric rows:", len(primary_metric_rows))
    print("Event rows valid:", report.is_valid, f"(rows={report.n_rows})")
    print("Exported artifacts:", ", ".join(path.name for path in exported_paths.values()))


if __name__ == "__main__":
    main()
