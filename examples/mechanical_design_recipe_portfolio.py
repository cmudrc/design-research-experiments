"""Mechanical design recipe-portfolio example.

## Introduction
Build and run a compact portfolio of study recipes around mechanical design
trade-offs such as bracket stiffness, truss weight, and manufacturability.

## Technical Implementation
1. Define a mechanical benchmark bundle plus recipe/config objects for
   bivariate and architecture-focused studies.
2. Materialize a compact bivariate study, execute it with deterministic mock
   agents, and export canonical analysis tables.
3. Print the generated study IDs and exported analysis artifacts for the
   mechanical-design portfolio.

## Expected Results
The script prints the recipe study IDs, the number of completed runs, and the
artifact filenames exported for downstream analysis.
"""

from __future__ import annotations

from pathlib import Path

import design_research_experiments as drex


def _mechanical_bundle() -> drex.BenchmarkBundle:
    """Return a small mechanical-design benchmark bundle."""
    return drex.BenchmarkBundle(
        bundle_id="mechanical-design",
        name="Mechanical Design Bundle",
        description=(
            "Bracket, truss, and enclosure redesign tasks for structural trade-off studies."
        ),
        problem_ids=("cantilever-bracket-redesign", "space-truss-joint"),
        agent_specs=("baseline-cad-agent", "constraint-aware-agent"),
        metadata={"domain": "mechanical-engineering"},
    )


def _problem_registry(problem_ids: tuple[str, ...]) -> dict[str, drex.ProblemPacket]:
    """Return a deterministic problem registry for mechanical design tasks."""

    def evaluator(output: dict[str, object]) -> list[dict[str, object]]:
        """Score one synthetic mechanical-design response."""
        text = str(output.get("text", ""))
        mass_score = round(min(0.95, 0.55 + len(text.split()) / 100.0), 4)
        return [{"metric_name": "primary_outcome", "metric_value": mass_score}]

    registry: dict[str, drex.ProblemPacket] = {}
    for problem_id in problem_ids:
        registry[problem_id] = drex.ProblemPacket(
            problem_id=problem_id,
            family="mechanical-design",
            brief=f"Design a lighter, stiffer concept for {problem_id}.",
            evaluator=evaluator,
        )
    return registry


def _agent_factory(agent_name: str):
    """Create a deterministic mechanical-design agent callable."""

    def _agent(
        *,
        problem_packet: drex.ProblemPacket,
        run_spec: drex.RunSpec,
        condition: drex.Condition,
    ) -> dict[str, object]:
        """Return one deterministic run payload for the requested condition."""
        comparison_arm = str(condition.factor_assignments.get("comparison_arm", "baseline"))
        prompt_regime = str(condition.factor_assignments.get("prompt_regime", "standard"))
        improvement_bonus = 0.07 if comparison_arm == "treatment" else 0.0
        structure_bonus = 0.03 if prompt_regime == "structured" else 0.0
        agent_bonus = 0.04 if agent_name == "constraint-aware-agent" else 0.0
        primary_outcome = round(0.58 + improvement_bonus + structure_bonus + agent_bonus, 4)
        text = (
            f"{agent_name} reviewed {problem_packet.problem_id} with "
            f"comparison_arm={comparison_arm} prompt_regime={prompt_regime} seed={run_spec.seed}"
        )
        return {
            "output": {"text": text},
            "metrics": {"primary_outcome": primary_outcome, "latency_s": 1.2},
            "events": [
                {"event_type": "assistant_output", "text": text, "actor_id": agent_name},
            ],
            "metadata": {"model_name": "example-mechanical-model"},
        }

    return _agent


def _portfolio_extensions() -> dict[str, object]:
    """Return study-building hooks that extend the mechanical portfolio."""
    return {
        "agent_architecture_config": drex.AgentArchitectureComparisonConfig,
        "benchmark_bundle": drex.BenchmarkBundle,
        "bivariate_config": drex.BivariateComparisonConfig,
        "block": drex.Block,
        "comparison_config": drex.ComparisonStudyConfig,
        "constraint": drex.Constraint,
        "diversity_config": drex.DiversityAndExplorationConfig,
        "export_analysis_tables": drex.export_analysis_tables,
        "grammar_scaffold_config": drex.GrammarScaffoldConfig,
        "human_vs_agent_config": drex.HumanVsAgentProcessConfig,
        "recipe_config": drex.RecipeStudyConfig,
        "resume_study": drex.resume_study,
        "run_result_type": drex.RunResult,
        "univariate_config": drex.UnivariateComparisonConfig,
    }


def main() -> None:
    """Build and execute a compact mechanical-design recipe portfolio."""
    mechanical_bundle = _mechanical_bundle()
    fabrication_block = drex.Block(name="mechanical_family", levels=("bracket", "truss"))
    manufacturability_constraint = drex.Constraint(
        constraint_id="structured-treatment-pairing",
        description="Treatment runs must use a structured prompt regime.",
        expression='comparison_arm != "treatment" or prompt_regime == "structured"',
    )

    portfolio_template = drex.RecipeStudyConfig(
        bundle=mechanical_bundle,
        output_dir=Path("artifacts") / "mechanical-design-portfolio",
    )
    comparison_template = drex.ComparisonStudyConfig(
        bundle=mechanical_bundle,
        blocks=(fabrication_block,),
    )
    bivariate_study = drex.build_bivariate_comparison_study(
        drex.BivariateComparisonConfig(
            bundle=mechanical_bundle,
            blocks=(fabrication_block,),
            constraints=(manufacturability_constraint,),
            run_budget=drex.RunBudget(replicates=1, parallelism=1, max_runs=4),
            output_dir=Path("artifacts") / "mechanical-bivariate-study",
        )
    )
    architecture_study = drex.build_agent_architecture_comparison_study(
        drex.AgentArchitectureComparisonConfig(
            bundle=mechanical_bundle,
            blocks=(fabrication_block,),
            output_dir=Path("artifacts") / "mechanical-architecture-study",
        )
    )
    univariate_study = drex.build_univariate_comparison_study(
        drex.UnivariateComparisonConfig(
            bundle=mechanical_bundle,
            blocks=(fabrication_block,),
        )
    )

    problem_registry = _problem_registry(bivariate_study.problem_ids)
    agent_bindings = {
        agent_name: (lambda _condition, *, _agent_name=agent_name: _agent_factory(_agent_name))
        for agent_name in bivariate_study.agent_specs
    }
    conditions = drex.build_design(bivariate_study)
    run_results = drex.run_study(
        bivariate_study,
        conditions=conditions,
        agent_bindings=agent_bindings,
        problem_registry=problem_registry,
        show_progress=False,
    )
    exported_paths = drex.export_analysis_tables(
        bivariate_study,
        conditions=conditions,
        run_results=run_results,
        output_dir=bivariate_study.output_dir / "analysis",
    )

    print("Portfolio template output dir:", portfolio_template.output_dir)
    print("Comparison template type:", type(comparison_template).__name__)
    print(
        "Studies:", bivariate_study.study_id, architecture_study.study_id, univariate_study.study_id
    )
    print("Completed runs:", len(run_results))
    print("RunResult objects:", all(isinstance(result, drex.RunResult) for result in run_results))
    print("Exported analysis tables:", ", ".join(path.name for path in exported_paths.values()))
    print("Portfolio extension hooks:", ", ".join(sorted(_portfolio_extensions())))


if __name__ == "__main__":
    main()
