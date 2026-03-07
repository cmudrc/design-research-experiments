"""Runnable PromptFramingRecipe example with mock agents/problems."""

from __future__ import annotations

from pathlib import Path

from design_research_experiments.adapters import ProblemPacket
from design_research_experiments.conditions import Condition
from design_research_experiments.recipes import PromptFramingRecipe
from design_research_experiments.reporting import render_markdown_summary, write_markdown_report
from design_research_experiments.runners import run_study
from design_research_experiments.study import RunSpec


def _build_problem_registry(problem_ids: tuple[str, ...]) -> dict[str, ProblemPacket]:
    """Build a lightweight in-memory problem registry for the example run."""

    def evaluator(output: dict[str, object]) -> list[dict[str, object]]:
        """Emit one deterministic evaluator row."""
        text = str(output.get("text", ""))
        return [{"metric_name": "novelty", "metric_value": len(text) / 100.0}]

    registry: dict[str, ProblemPacket] = {}
    for problem_id in problem_ids:
        registry[problem_id] = ProblemPacket(
            problem_id=problem_id,
            family="ideation",
            brief=f"Ideation brief for {problem_id}",
            evaluator=evaluator,
        )
    return registry


def _agent_factory(agent_name: str):
    """Create a deterministic agent callable for one recipe arm."""

    def _agent(
        *, problem_packet: ProblemPacket, run_spec: RunSpec, condition: Condition
    ) -> dict[str, object]:
        """Generate one deterministic mock run result for prompt-framing conditions."""
        run_seed = run_spec.seed
        factor_assignments = condition.factor_assignments
        prompt_frame = str(factor_assignments.get("prompt_frame", "neutral"))
        prompt_difficulty = str(factor_assignments.get("prompt_difficulty", "low"))

        frame_bonus = (
            0.08 if prompt_frame == "analogy" else 0.04 if prompt_frame == "challenge" else 0.0
        )
        difficulty_bonus = 0.03 if prompt_difficulty == "high" else 0.0
        agent_bonus = 0.04 if agent_name == "creative-agent" else 0.0
        primary_outcome = round(0.50 + frame_bonus + difficulty_bonus + agent_bonus, 4)

        text = (
            f"{agent_name} solved {problem_packet.problem_id} "
            f"with frame={prompt_frame} difficulty={prompt_difficulty} seed={run_seed}"
        )

        return {
            "output": {"text": text},
            "metrics": {
                "primary_outcome": primary_outcome,
                "input_tokens": 120,
                "output_tokens": 220,
                "cost_usd": 0.015,
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
    """Run a compact PromptFramingRecipe study and write a markdown summary."""
    study = PromptFramingRecipe().build_study()
    study.output_dir = Path("artifacts") / "example-prompt-framing"
    study.problem_ids = ("ideation-1", "ideation-2")
    study.run_budget.replicates = 1
    study.run_budget.parallelism = 1
    study.run_budget.max_runs = 6

    problem_registry = _build_problem_registry(study.problem_ids)
    agent_factories = {
        "baseline-agent": lambda _condition: _agent_factory("baseline-agent"),
        "creative-agent": lambda _condition: _agent_factory("creative-agent"),
    }

    run_results = run_study(
        study,
        agent_factories=agent_factories,
        problem_registry=problem_registry,
        include_sqlite=True,
    )

    summary = render_markdown_summary(study, run_results)
    summary_path = write_markdown_report(study.output_dir, "prompt_framing_summary.md", summary)

    print(f"Completed {len(run_results)} runs")
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
