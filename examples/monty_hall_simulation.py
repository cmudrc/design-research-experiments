"""Monty Hall simulation example.

## Introduction
Model the Monty Hall game as a tiny two-condition ``drex.Study`` and simulate
100 random games for each strategy to show why switching usually wins more
often than staying.

## Technical Implementation
1. Define a study with one manipulated factor (``strategy``) and two levels:
   ``stay`` and ``switch``.
2. Validate the study and materialize the two conditions with
   ``drex.build_design``.
3. Pass a typed condition callback to ``drex.run_study`` so the standard runner
   owns deterministic seeds, result normalization, and canonical artifacts.

## Expected Results
The script completes 2 conditions, simulates 100 games per condition, reports
``stay`` winning ``32/100`` and ``switch`` winning ``70/100``, and writes the
canonical artifact set under ``artifacts/monty-hall``.
"""

from __future__ import annotations

import random
from pathlib import Path

import design_research_experiments as drex

DOORS = ("A", "B", "C")
SIMULATED_GAMES = 100
SIMULATION_SEED = 5


def build_monty_hall_study(output_dir: Path) -> drex.Study:
    """Build a study with one condition per contestant strategy."""
    return drex.Study(
        study_id="monty-hall-simulation",
        title="Monty Hall Simulation",
        description=(
            "Compare stay versus switch by simulating random Monty Hall games "
            "inside each study condition."
        ),
        factors=(
            drex.Factor(
                name="strategy",
                description="Contestant decision after the host reveals a goat door.",
                kind=drex.FactorKind.MANIPULATED,
                levels=(
                    drex.Level(name="stay", value="stay"),
                    drex.Level(name="switch", value="switch"),
                ),
            ),
        ),
        hypotheses=(
            drex.Hypothesis(
                hypothesis_id="h1",
                label="Switching improves win rate",
                statement="Switching wins more often than staying in the Monty Hall game.",
                independent_vars=("strategy",),
                dependent_vars=("win_rate",),
            ),
        ),
        outcomes=(
            drex.OutcomeSpec(
                name="win_rate",
                source_table="runs",
                column="won",
                aggregation="mean",
                primary=True,
                description="Share of scored conditions that end with the prize.",
            ),
        ),
        analysis_plans=(
            drex.AnalysisPlan(
                analysis_plan_id="ap1",
                hypothesis_ids=("h1",),
                tests=("simulation_summary",),
                outcomes=("win_rate",),
            ),
        ),
        design_spec=drex.DesignSpec(kind=drex.DesignKind.FULL_FACTORIAL),
        seed_policy=drex.SeedPolicy(base_seed=SIMULATION_SEED),
        output_dir=output_dir,
    )


def reveal_goat_door(*, prize_door: str, initial_choice: str, rng: random.Random) -> str:
    """Randomly reveal one admissible goat door."""
    goat_doors = [door for door in DOORS if door != prize_door and door != initial_choice]
    if not goat_doors:
        raise RuntimeError("Expected at least one goat door to reveal.")
    return str(rng.choice(goat_doors))


def resolve_final_choice(*, initial_choice: str, revealed_door: str, strategy: str) -> str:
    """Return the contestant's final door after staying or switching."""
    if strategy == "stay":
        return initial_choice

    for door in DOORS:
        if door != initial_choice and door != revealed_door:
            return door
    raise RuntimeError("Expected exactly one switch target.")


def simulate_condition(
    run_spec: drex.RunSpec,
    condition: drex.Condition,
) -> drex.RunOutput:
    """Simulate one strategy condition with the runner-provided seed."""
    assignments = condition.factor_assignments
    strategy = str(assignments["strategy"])
    rng = random.Random(run_spec.seed)
    wins = 0

    for _ in range(SIMULATED_GAMES):
        prize_door = str(rng.choice(DOORS))
        initial_choice = str(rng.choice(DOORS))
        revealed_door = reveal_goat_door(
            prize_door=prize_door,
            initial_choice=initial_choice,
            rng=rng,
        )
        final_choice = resolve_final_choice(
            initial_choice=initial_choice,
            revealed_door=revealed_door,
            strategy=strategy,
        )
        wins += int(final_choice == prize_door)

    win_rate = round(wins / SIMULATED_GAMES, 2)
    return drex.RunOutput(
        outputs={
            "condition_id": condition.condition_id,
            "strategy": strategy,
            "seed": run_spec.seed,
            "games": SIMULATED_GAMES,
            "wins": wins,
            "win_rate": win_rate,
        },
        metrics={"primary_outcome": win_rate, "win_rate": win_rate},
    )


def lookup_strategy(rows: list[dict[str, object]], *, strategy: str) -> dict[str, object]:
    """Return the summary row for one strategy."""
    for row in rows:
        if row["strategy"] == strategy:
            return row
    raise RuntimeError(f"Missing strategy summary for {strategy!r}.")


def main() -> None:
    """Run random Monty Hall games through standalone study orchestration."""
    output_dir = Path("artifacts") / "monty-hall"
    study = build_monty_hall_study(output_dir)

    errors = drex.validate_study(study)
    if errors:
        raise RuntimeError("\n".join(errors))

    runner: drex.ConditionRunner = simulate_condition
    results = drex.run_study(
        study,
        condition_runner=runner,
        show_progress=False,
    )
    rows = [result.outputs for result in results]

    stay = lookup_strategy(rows, strategy="stay")
    switch = lookup_strategy(rows, strategy="switch")

    if float(switch["win_rate"]) <= float(stay["win_rate"]):
        raise RuntimeError("Switching should strictly outperform staying in Monty Hall.")

    print(f"Completed {len(results)} conditions")
    print(f"Simulated {SIMULATED_GAMES} games per condition")
    print(f"stay wins {stay['wins']}/{stay['games']} = {stay['win_rate']:.2f}")
    print(f"switch wins {switch['wins']}/{switch['games']} = {switch['win_rate']:.2f}")
    print(f"Wrote canonical artifacts to {output_dir}")


if __name__ == "__main__":
    main()
