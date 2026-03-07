"""Optimization-benchmark recipe execution example.

## Introduction
Execute a non-default optimization benchmark recipe with deterministic mocks.

## Technical Implementation
1. Build ``OptimizationBenchmarkConfig`` overrides for factors and design.
2. Create deterministic problem packets and per-agent factories.
3. Run the study and write methods/significance/codebook markdown output.

## Expected Results
The script prints completed run count and writes
``artifacts/example-optimization-benchmark/artifacts/optimization_benchmark_report.md``.
"""

from __future__ import annotations

from pathlib import Path

import design_research_experiments as drex


def _build_problem_registry(problem_ids: tuple[str, ...]) -> dict[str, drex.ProblemPacket]:
    """Build a deterministic optimization-oriented problem registry."""

    def evaluator(output: dict[str, object]) -> list[dict[str, object]]:
        """Emit one deterministic optimization score row."""
        text = str(output.get("text", ""))
        return [{"metric_name": "objective_score", "metric_value": len(text) / 120.0}]

    registry: dict[str, drex.ProblemPacket] = {}
    for problem_id in problem_ids:
        registry[problem_id] = drex.ProblemPacket(
            problem_id=problem_id,
            family="optimization",
            brief=f"Optimization benchmark brief for {problem_id}",
            evaluator=evaluator,
        )
    return registry


def _agent_factory(agent_name: str):
    """Create a deterministic optimization agent callable."""

    def _agent(
        *,
        problem_packet: drex.ProblemPacket,
        run_spec: drex.RunSpec,
        condition: drex.Condition,
    ) -> dict[str, object]:
        """Generate one deterministic mock run result for optimization conditions."""
        run_seed = run_spec.seed
        factor_assignments = condition.factor_assignments
        learning_strategy = str(
            factor_assignments.get("learning_strategy", "deterministic-baseline")
        )
        tuning_regime = str(factor_assignments.get("tuning_regime", "conservative"))

        strategy_bonus = 0.08 if learning_strategy == "self-learning-agent" else 0.0
        tuning_bonus = 0.04 if tuning_regime == "aggressive" else 0.0
        agent_bonus = 0.03 if agent_name == "self-learning-agent" else 0.0
        primary_outcome = round(0.56 + strategy_bonus + tuning_bonus + agent_bonus, 4)

        text = (
            f"{agent_name} optimized {problem_packet.problem_id} "
            f"with strategy={learning_strategy} tuning={tuning_regime} seed={run_seed}"
        )

        return {
            "output": {"text": text},
            "metrics": {
                "primary_outcome": primary_outcome,
                "input_tokens": 150,
                "output_tokens": 240,
                "cost_usd": 0.022,
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
    """Run an optimization benchmark study and export markdown artifacts."""
    config = drex.OptimizationBenchmarkConfig(
        study_id="optimization-benchmark-custom",
        factors=(
            drex.Factor(
                name="learning_strategy",
                description="Agent learning approach.",
                kind=drex.FactorKind.MANIPULATED,
                levels=(
                    drex.Level(name="deterministic", value="deterministic-baseline"),
                    drex.Level(name="self_learning", value="self-learning-agent"),
                ),
            ),
            drex.Factor(
                name="tuning_regime",
                description="Hyperparameter regime.",
                kind=drex.FactorKind.MANIPULATED,
                levels=(
                    drex.Level(name="conservative", value="conservative"),
                    drex.Level(name="aggressive", value="aggressive"),
                    drex.Level(name="exploratory", value="exploratory"),
                ),
            ),
        ),
        design_spec={"kind": "randomized_block", "randomize": True},
        run_budget=drex.RunBudget(replicates=1, parallelism=1, max_runs=8),
        output_dir=Path("artifacts") / "example-optimization-benchmark",
        problem_ids=("optimization-small", "optimization-medium"),
        agent_specs=("deterministic-baseline", "self-learning-agent"),
    )
    study = drex.build_optimization_benchmark_study(config)

    problem_registry = _build_problem_registry(study.problem_ids)
    agent_factories = {
        "deterministic-baseline": lambda _condition: _agent_factory("deterministic-baseline"),
        "self-learning-agent": lambda _condition: _agent_factory("self-learning-agent"),
    }

    run_results = drex.run_study(
        study,
        agent_factories=agent_factories,
        problem_registry=problem_registry,
    )

    condition_ids = {
        result.run_spec.condition_id for result in run_results if result.run_spec is not None
    }
    significance = drex.render_significance_brief(
        [
            {
                "test": "mixed_effects",
                "outcome": "primary_outcome",
                "p_value": 0.04,
                "effect_size": 0.37,
            }
        ]
    )
    methods = drex.render_methods_scaffold(study)
    codebook = drex.render_codebook(
        study,
        [
            condition
            for condition in drex.build_design(study)
            if condition.condition_id in condition_ids
        ],
    )

    report = "\n\n".join((methods, significance, codebook))
    report_path = drex.write_markdown_report(
        study.output_dir, "optimization_benchmark_report.md", report
    )

    print(f"Completed {len(run_results)} runs")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
