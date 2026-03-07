"""Recipe overview example.

## Introduction
Survey the reusable recipe builders and reporting helpers without running a study.

## Technical Implementation
1. Instantiate each recipe factory once.
2. Load standard benchmark bundles.
3. Render markdown summary, methods scaffold, and codebook snippets.

## Expected Results
The script prints bundle counts and markdown snippets that confirm recipe objects
and reporting helpers are wired correctly.
"""

from __future__ import annotations

from pathlib import Path

import design_research_experiments as drex


def main() -> None:
    """Build recipe studies and render lightweight markdown outputs."""
    studies = (
        drex.build_agent_architecture_comparison_study(),
        drex.build_prompt_framing_study(),
        drex.build_grammar_scaffold_study(),
        drex.build_human_vs_agent_process_study(),
        drex.build_diversity_and_exploration_study(),
        drex.build_optimization_benchmark_study(),
    )
    bundles = (
        drex.ideation_bundle(),
        drex.optimization_bundle(),
        drex.grammar_problem_bundle(),
        drex.human_vs_agent_bundle(),
    )

    print(f"Loaded {len(bundles)} benchmark bundles")

    first_study = studies[0]
    first_study.output_dir = Path("artifacts") / "recipe-overview"
    conditions = drex.build_design(first_study)

    print(drex.render_markdown_summary(first_study, run_results=[]))
    print(drex.render_methods_scaffold(first_study))
    print(drex.render_codebook(first_study, conditions[:2]))


if __name__ == "__main__":
    main()
