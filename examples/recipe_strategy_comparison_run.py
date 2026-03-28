"""Strategy-comparison recipe execution example.

## Introduction
Execute a packaged-problem strategy comparison study with deterministic mocks.

## Technical Implementation
1. Build ``StrategyComparisonConfig`` overrides for bundle selection, run budget, and output path.
2. Create deterministic problem packets and one factory per compared agent strategy.
3. Run the study and write a markdown summary artifact.

## Expected Results
The script prints completed run count and writes
``artifacts/example-strategy-comparison/artifacts/strategy_comparison_summary.md``.
"""

from __future__ import annotations

from pathlib import Path

import design_research_experiments as drex


def _build_problem_registry(problem_ids: tuple[str, ...]) -> dict[str, drex.ProblemPacket]:
    """Build a deterministic optimization-style problem registry."""

    def evaluator(output: dict[str, object]) -> list[dict[str, object]]:
        """Emit one synthetic benchmark metric row."""
        text = str(output.get("text", ""))
        return [{"metric_name": "objective_score", "metric_value": len(text) / 110.0}]

    registry: dict[str, drex.ProblemPacket] = {}
    for problem_id in problem_ids:
        registry[problem_id] = drex.ProblemPacket(
            problem_id=problem_id,
            family="optimization",
            brief=f"Packaged benchmark brief for {problem_id}",
            evaluator=evaluator,
        )
    return registry


def _agent_factory(agent_name: str):
    """Create a deterministic strategy-specific agent callable."""

    def _agent(
        *,
        problem_packet: drex.ProblemPacket,
        run_spec: drex.RunSpec,
        condition: drex.Condition,
    ) -> dict[str, object]:
        """Generate one deterministic mock run result for strategy comparisons."""
        compared_agent = str(condition.factor_assignments.get("agent_id", agent_name))
        run_seed = run_spec.seed
        strategy_bonus = 0.09 if compared_agent == "self-learning-agent" else 0.0
        baseline_bonus = 0.03 if "baseline" in compared_agent else 0.0
        family_bonus = 0.02 if problem_packet.problem_id.endswith("medium") else 0.0
        primary_outcome = round(0.55 + strategy_bonus + baseline_bonus + family_bonus, 4)

        text = (
            f"{compared_agent} solved {problem_packet.problem_id} "
            f"with seed={run_seed} condition={condition.condition_id}"
        )

        return {
            "output": {"text": text},
            "metrics": {
                "primary_outcome": primary_outcome,
                "input_tokens": 130,
                "output_tokens": 210,
                "cost_usd": 0.019,
            },
            "events": [
                {
                    "event_type": "assistant_output",
                    "text": text,
                    "actor_id": compared_agent,
                }
            ],
            "metadata": {"model_name": "example-model"},
        }

    return _agent


def main() -> None:
    """Run a packaged-problem strategy comparison study and write a summary artifact."""
    config = drex.StrategyComparisonConfig(
        bundle=drex.optimization_bundle(),
        run_budget=drex.RunBudget(replicates=1, parallelism=1, max_runs=4),
        output_dir=Path("artifacts") / "example-strategy-comparison",
        problem_ids=("optimization-small", "optimization-medium"),
    )
    study = drex.build_strategy_comparison_study(config)

    strategy_ids = tuple(str(level.value) for level in study.factors[0].levels)
    problem_registry = _build_problem_registry(study.problem_ids)
    agent_factories = {
        strategy_id: (lambda _condition, strategy_id=strategy_id: _agent_factory(strategy_id))
        for strategy_id in strategy_ids
    }

    run_results = drex.run_study(
        study,
        agent_factories=agent_factories,
        problem_registry=problem_registry,
    )

    summary = drex.render_markdown_summary(study, run_results)
    summary_path = drex.write_markdown_report(
        study.output_dir,
        "strategy_comparison_summary.md",
        summary,
    )

    print(f"Completed {len(run_results)} runs")
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
