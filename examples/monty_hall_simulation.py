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
3. Simulate 100 seeded random Monty Hall games for each condition, write a
   summary CSV artifact, and print the resulting win counts.

## Expected Results
The script prints 2 materialized conditions, simulates 100 games per condition
with a fixed seed, reports ``stay`` winning ``35/100`` and ``switch`` winning
``65/100``, and writes a summary CSV artifact under ``artifacts/monty-hall``.
"""

from __future__ import annotations

import csv
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
                linked_analysis_plan_id="ap1",
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
        design_spec={"kind": "full_factorial", "randomize": False},
        seed_policy=drex.SeedPolicy(base_seed=SIMULATION_SEED),
        output_dir=output_dir,
        problem_ids=("monty-hall-game",),
        primary_outcomes=("win_rate",),
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


def simulate_condition(condition: drex.Condition, *, n_games: int, seed: int) -> dict[str, object]:
    """Simulate one strategy condition over many random Monty Hall games."""
    assignments = condition.factor_assignments
    strategy = str(assignments["strategy"])
    rng = random.Random(seed)
    wins = 0

    for _ in range(n_games):
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

    return {
        "condition_id": condition.condition_id,
        "strategy": strategy,
        "seed": seed,
        "games": n_games,
        "wins": wins,
        "win_rate": round(wins / n_games, 2),
    }


def write_summary(path: Path, rows: list[dict[str, object]]) -> None:
    """Write the per-condition simulation summary as a CSV artifact."""
    if not rows:
        raise RuntimeError("Expected scored rows before writing artifacts.")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def lookup_strategy(rows: list[dict[str, object]], *, strategy: str) -> dict[str, object]:
    """Return the summary row for one strategy."""
    for row in rows:
        if row["strategy"] == strategy:
            return row
    raise RuntimeError(f"Missing strategy summary for {strategy!r}.")


def main() -> None:
    """Simulate random Monty Hall games for each strategy condition."""
    output_dir = Path("artifacts") / "monty-hall"
    study = build_monty_hall_study(output_dir)

    errors = drex.validate_study(study)
    if errors:
        raise RuntimeError("\n".join(errors))

    conditions = drex.build_design(study)
    rows = [
        simulate_condition(
            condition,
            n_games=SIMULATED_GAMES,
            seed=study.seed_policy.base_seed,
        )
        for condition in conditions
    ]

    csv_path = output_dir / "simulation_summary.csv"
    write_summary(csv_path, rows)

    stay = lookup_strategy(rows, strategy="stay")
    switch = lookup_strategy(rows, strategy="switch")

    if float(switch["win_rate"]) <= float(stay["win_rate"]):
        raise RuntimeError("Switching should strictly outperform staying in Monty Hall.")

    print(f"Materialized {len(conditions)} conditions")
    print(
        f"Simulated {SIMULATED_GAMES} games per condition with seed {study.seed_policy.base_seed}"
    )
    print(f"stay wins {stay['wins']}/{stay['games']} = {stay['win_rate']:.2f}")
    print(f"switch wins {switch['wins']}/{switch['games']} = {switch['win_rate']:.2f}")
    print(f"Wrote simulation summary CSV to {csv_path}")


if __name__ == "__main__":
    main()
