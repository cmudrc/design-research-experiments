"""Real-stack interoperability example.

## Introduction
Run one packaged problem from `design-research-problems` through a public
`design-research-agents` baseline and validate the exported `events.csv`
contract with `design-research-analysis`.

## Technical Implementation
1. Bootstrap sibling `src/` directories from the local workspace when present.
2. Execute a one-run study that uses a packaged optimization problem together
   with `SeededRandomBaselineAgent`.
3. Export canonical artifacts and validate the event table through the analysis
   package's unified-table contract.

## Expected Results
The script prints the packaged problem identity, one successful run result, and
the exported artifact filenames after the event table passes validation.
"""

from __future__ import annotations

import csv
import importlib
import sys
from pathlib import Path

import design_research_experiments as drex


def _bootstrap_sibling_sources() -> None:
    """Add sibling package `src/` directories when the repos are checked out locally."""
    workspace_root = Path(__file__).resolve().parents[2]
    for repo_name in (
        "design-research-problems",
        "design-research-agents",
        "design-research-analysis",
    ):
        src_path = workspace_root / repo_name / "src"
        src_path_text = str(src_path)
        if src_path.exists() and src_path_text not in sys.path:
            sys.path.insert(0, src_path_text)


def _load_stack_modules() -> dict[str, object] | None:
    """Import sibling stack packages when available from the local workspace."""
    _bootstrap_sibling_sources()
    try:
        problems_module = importlib.import_module("design_research_problems")
        importlib.import_module("design_research_agents")
    except ImportError as exc:
        print(f"Real stack example skipped: {exc}")
        return None

    try:
        analysis_module = importlib.import_module("design_research_analysis")
    except ImportError:
        try:
            analysis_module = importlib.import_module("design_research_analysis.table")
        except ImportError as exc:
            print(f"Real stack example skipped: {exc}")
            return None

    return {
        "problems": problems_module,
        "analysis": analysis_module,
    }


def main() -> None:
    """Run one real interoperability path across the sibling libraries."""
    modules = _load_stack_modules()
    if modules is None:
        return

    problems_module = modules["problems"]
    analysis_module = modules["analysis"]
    problem_id = "gmpb_default_dynamic_min"
    packaged_problem = problems_module.get_problem(problem_id)

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
    run_results = drex.run_study(study, conditions=conditions, show_progress=False)
    exported_paths = drex.export_analysis_tables(
        study,
        conditions=conditions,
        run_results=run_results,
        output_dir=study.output_dir / "analysis",
        validate_with_analysis_package=True,
    )

    with exported_paths["events.csv"].open("r", encoding="utf-8", newline="") as file_obj:
        rows = list(csv.DictReader(file_obj))
    report = analysis_module.validate_unified_table(
        analysis_module.coerce_unified_table(rows)
    )
    run_result = run_results[0]

    print("Problem ID:", packaged_problem.metadata.problem_id)
    print("Problem family:", packaged_problem.metadata.kind.value)
    print("Agent:", study.agent_specs[0])
    print("Completed runs:", len(run_results))
    print("Run status:", run_result.status.value)
    print("Output keys:", ", ".join(sorted(run_result.outputs)))
    print("Primary outcome:", run_result.metrics.get("primary_outcome"))
    print("Event rows valid:", report.is_valid, f"(rows={report.n_rows})")
    print("Exported artifacts:", ", ".join(path.name for path in exported_paths.values()))


if __name__ == "__main__":
    main()
