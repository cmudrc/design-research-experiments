"""Prompt-framing recipe execution example.

## Introduction
Execute a non-default prompt-framing recipe with deterministic mock components.

## Technical Implementation
1. Build ``PromptFramingConfig`` overrides for factors, design, budget, and IDs.
2. Create deterministic in-memory problem and agent adapters.
3. Run the study and write a markdown summary artifact.

## Expected Results
The script prints completed run count and writes
``artifacts/example-prompt-framing/artifacts/prompt_framing_summary.md``.
"""

from __future__ import annotations

from pathlib import Path

import design_research_experiments as drex


def _build_problem_registry(problem_ids: tuple[str, ...]) -> dict[str, drex.ProblemPacket]:
    """Build a lightweight in-memory problem registry for the example run."""

    def evaluator(output: dict[str, object]) -> list[dict[str, object]]:
        """Emit one deterministic evaluator row."""
        text = str(output.get("text", ""))
        return [{"metric_name": "novelty", "metric_value": len(text) / 100.0}]

    registry: dict[str, drex.ProblemPacket] = {}
    for problem_id in problem_ids:
        registry[problem_id] = drex.ProblemPacket(
            problem_id=problem_id,
            family="ideation",
            brief=f"Ideation brief for {problem_id}",
            evaluator=evaluator,
        )
    return registry


def _agent_factory(agent_name: str):
    """Create a deterministic agent callable for one recipe arm."""

    def _agent(
        *,
        problem_packet: drex.ProblemPacket,
        run_spec: drex.RunSpec,
        condition: drex.Condition,
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
    """Run a prompt-framing study with non-default typed recipe overrides."""
    config = drex.PromptFramingConfig(
        study_id="prompt-framing-custom",
        bundle=drex.ideation_bundle(),
        # Replace sections wholesale with non-default recipe choices.
        factors=(
            drex.Factor(
                name="prompt_frame",
                description="Prompt framing style.",
                kind=drex.FactorKind.MANIPULATED,
                levels=(
                    drex.Level(name="neutral", value="neutral"),
                    drex.Level(name="challenge", value="challenge"),
                    drex.Level(name="analogy", value="analogy"),
                    drex.Level(name="counterfactual", value="counterfactual"),
                ),
            ),
            drex.Factor(
                name="prompt_difficulty",
                description="Prompt difficulty.",
                kind=drex.FactorKind.MANIPULATED,
                levels=(
                    drex.Level(name="low", value="low"),
                    drex.Level(name="high", value="high"),
                ),
            ),
        ),
        design_spec={"kind": "constrained_factorial", "randomize": True},
        run_budget=drex.RunBudget(replicates=1, parallelism=1, max_runs=8),
        output_dir=Path("artifacts") / "example-prompt-framing",
        # Explicit values override bundle-provided IDs.
        problem_ids=("ideation-brief-a", "ideation-brief-b"),
        agent_specs=("baseline-agent", "creative-agent"),
    )
    study = drex.build_prompt_framing_study(config)

    problem_registry = _build_problem_registry(study.problem_ids)
    agent_factories = {
        "baseline-agent": lambda _condition: _agent_factory("baseline-agent"),
        "creative-agent": lambda _condition: _agent_factory("creative-agent"),
    }

    run_results = drex.run_study(
        study,
        agent_factories=agent_factories,
        problem_registry=problem_registry,
        include_sqlite=True,
    )

    summary = drex.render_markdown_summary(study, run_results)
    summary_path = drex.write_markdown_report(
        study.output_dir,
        "prompt_framing_summary.md",
        summary,
    )

    print(f"Completed {len(run_results)} runs")
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
