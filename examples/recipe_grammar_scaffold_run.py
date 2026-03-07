"""Runnable GrammarScaffoldRecipe example with mock agents/problems."""

from __future__ import annotations

from pathlib import Path

from design_research_experiments.adapters import ProblemPacket
from design_research_experiments.conditions import Condition
from design_research_experiments.designs import build_design
from design_research_experiments.recipes import GrammarScaffoldRecipe
from design_research_experiments.reporting import (
    render_codebook,
    render_methods_scaffold,
    render_significance_brief,
    write_markdown_report,
)
from design_research_experiments.runners import run_study
from design_research_experiments.study import RunSpec


def _build_problem_registry(problem_ids: tuple[str, ...]) -> dict[str, ProblemPacket]:
    """Build a small grammar-focused problem registry."""

    def evaluator(output: dict[str, object]) -> list[dict[str, object]]:
        """Emit one deterministic quality score row."""
        text = str(output.get("text", ""))
        return [{"metric_name": "grammar_quality", "metric_value": len(set(text.split())) / 50.0}]

    registry: dict[str, ProblemPacket] = {}
    for problem_id in problem_ids:
        registry[problem_id] = ProblemPacket(
            problem_id=problem_id,
            family="grammar",
            brief=f"Grammar generation brief for {problem_id}",
            evaluator=evaluator,
        )
    return registry


def _agent_factory(agent_name: str):
    """Create a deterministic grammar agent callable."""

    def _agent(
        *, problem_packet: ProblemPacket, run_spec: RunSpec, condition: Condition
    ) -> dict[str, object]:
        """Generate one deterministic mock run result for grammar-scaffold conditions."""
        run_seed = run_spec.seed
        factor_assignments = condition.factor_assignments
        generation_mode = str(factor_assignments.get("generation_mode", "unconstrained"))

        mode_bonus = {
            "unconstrained": 0.00,
            "grammar-guided": 0.10,
            "tool-guided": 0.14,
        }.get(generation_mode, 0.00)
        agent_bonus = 0.03 if agent_name == "workflow-agent" else 0.0
        primary_outcome = round(0.52 + mode_bonus + agent_bonus, 4)

        text = (
            f"{agent_name} generated solution for {problem_packet.problem_id} "
            f"with mode={generation_mode} seed={run_seed}"
        )

        return {
            "output": {"text": text},
            "metrics": {
                "primary_outcome": primary_outcome,
                "input_tokens": 140,
                "output_tokens": 260,
                "cost_usd": 0.018,
            },
            "events": [
                {
                    "event_type": "assistant_output",
                    "text": text,
                    "actor_id": agent_name,
                }
            ],
            "metadata": {"model_name": "example-model"},
        }

    return _agent


def main() -> None:
    """Run a compact GrammarScaffoldRecipe study and export markdown artifacts."""
    study = GrammarScaffoldRecipe().build_study()
    study.output_dir = Path("artifacts") / "example-grammar-scaffold"
    study.problem_ids = ("grammar-1",)
    study.run_budget.replicates = 1
    study.run_budget.parallelism = 1
    study.run_budget.max_runs = 6

    problem_registry = _build_problem_registry(study.problem_ids)
    agent_factories = {
        "direct-llm": lambda _condition: _agent_factory("direct-llm"),
        "workflow-agent": lambda _condition: _agent_factory("workflow-agent"),
    }

    run_results = run_study(
        study,
        agent_factories=agent_factories,
        problem_registry=problem_registry,
    )

    condition_ids = {
        result.run_spec.condition_id for result in run_results if result.run_spec is not None
    }
    significance = render_significance_brief(
        [
            {
                "test": "difference_in_means",
                "outcome": "primary_outcome",
                "p_value": 0.03,
                "effect_size": 0.41,
            }
        ]
    )
    methods = render_methods_scaffold(study)
    codebook = render_codebook(
        study,
        [condition for condition in build_design(study) if condition.condition_id in condition_ids],
    )

    report = "\n\n".join((methods, significance, codebook))
    report_path = write_markdown_report(study.output_dir, "grammar_scaffold_report.md", report)

    print(f"Completed {len(run_results)} runs")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
