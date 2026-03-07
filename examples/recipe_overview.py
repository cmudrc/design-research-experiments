"""Recipe and reporting overview for design-research-experiments."""

from __future__ import annotations

from pathlib import Path

from design_research_experiments.bundles import (
    grammar_problem_bundle,
    human_vs_agent_bundle,
    ideation_bundle,
    optimization_bundle,
)
from design_research_experiments.designs import build_design
from design_research_experiments.recipes import (
    AgentArchitectureComparisonRecipe,
    DiversityAndExplorationRecipe,
    GrammarScaffoldRecipe,
    HumanVsAgentProcessRecipe,
    PromptFramingRecipe,
)
from design_research_experiments.reporting import (
    render_codebook,
    render_markdown_summary,
    render_methods_scaffold,
)


def main() -> None:
    """Build recipe studies and render lightweight markdown outputs."""
    recipe_builders = (
        AgentArchitectureComparisonRecipe(),
        PromptFramingRecipe(),
        GrammarScaffoldRecipe(),
        HumanVsAgentProcessRecipe(),
        DiversityAndExplorationRecipe(),
    )
    bundles = (
        ideation_bundle(),
        optimization_bundle(),
        grammar_problem_bundle(),
        human_vs_agent_bundle(),
    )

    print(f"Loaded {len(bundles)} benchmark bundles")

    first_study = recipe_builders[0].build_study()
    first_study.output_dir = Path("artifacts") / "recipe-overview"
    conditions = build_design(first_study)

    print(render_markdown_summary(first_study, run_results=[]))
    print(render_methods_scaffold(first_study))
    print(render_codebook(first_study, conditions[:2]))


if __name__ == "__main__":
    main()
