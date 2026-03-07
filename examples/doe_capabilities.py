"""DOE generation capability example.

## Introduction
Demonstrate one-shot DOE generation for full-factorial, LHS, and frac2 designs.

## Technical Implementation
1. Generate three DOE tables with ``drex.generate_doe``.
2. Write the LHS table to ``artifacts/doe-capabilities/lhs_design.csv``.
3. Print run counts for quick sanity checks.

## Expected Results
The script reports run counts for each design type and confirms the CSV artifact
path for the generated LHS table.
"""

from __future__ import annotations

import csv
from pathlib import Path

import design_research_experiments as drex


def main() -> None:
    """Generate representative DOE tables and write one CSV artifact."""
    full = drex.generate_doe(
        kind="full",
        factors={"a": [0, 1], "b": [10, 20, 30]},
        randomize=False,
    )
    lhs = drex.generate_doe(
        kind="lhs",
        factors={"x": [0.0, 1.0], "y": [10.0, 20.0]},
        n_samples=8,
        seed=7,
        randomize=True,
    )
    frac2 = drex.generate_doe(
        kind="frac2",
        factors={"a": [0, 1], "b": [0, 1], "c": [0, 1], "d": [0, 1]},
        randomize=False,
    )

    out_dir = Path("artifacts") / "doe-capabilities"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "lhs_design.csv"
    rows = lhs["design"]
    fieldnames = list(lhs["summary"]["factors"])
    with csv_path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Full factorial runs: {full['summary']['n_runs']}")
    print(f"LHS runs: {lhs['summary']['n_runs']}")
    print(f"Frac2 runs: {frac2['summary']['n_runs']}")
    print(f"Wrote LHS design CSV to {csv_path}")


if __name__ == "__main__":
    main()
