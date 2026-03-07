"""DOE capability tests migrated from drcutils-style workflows."""

from __future__ import annotations

import pytest

from design_research_experiments.conditions import Factor, FactorKind, Level
from design_research_experiments.designs import (
    build_design,
    fractional_factorial_2level,
    full_factorial,
    generate_doe,
    latin_hypercube,
    randomize_runs,
)
from design_research_experiments.schemas import ValidationError

from .helpers import make_study


def test_full_factorial_row_count_matches_level_product() -> None:
    """Full factorial utility should generate every explicit level combination."""
    design = full_factorial({"a": [0, 1], "b": [10, 20, 30]})
    assert len(design) == 6


def test_latin_hypercube_is_seed_deterministic_and_bounded() -> None:
    """Latin-hypercube generation should be deterministic for one seed."""
    factors = {"x": (0.0, 1.0), "y": (10.0, 20.0)}
    d1 = latin_hypercube(8, factors=factors, seed=4)
    d2 = latin_hypercube(8, factors=factors, seed=4)

    assert d1 == d2
    assert len(d1) == 8
    assert all(0.0 <= float(row["x"]) <= 1.0 for row in d1)
    assert all(10.0 <= float(row["y"]) <= 20.0 for row in d1)


def test_fractional_factorial_two_level_supports_resolution_three_templates() -> None:
    """Fractional 2-level utility should provide coded +/-1 rows for up to 6 factors."""
    rows = fractional_factorial_2level(["a", "b", "c", "d"], resolution="III")

    assert len(rows) == 8
    assert set(rows[0]) == {"a", "b", "c", "d"}
    assert {value for row in rows for value in row.values()} == {-1.0, 1.0}


def test_randomize_runs_supports_within_block_randomization() -> None:
    """Run randomization should preserve block grouping while shuffling rows per block."""
    rows = [
        {"block": "a", "run": 1},
        {"block": "a", "run": 2},
        {"block": "b", "run": 3},
        {"block": "b", "run": 4},
    ]
    randomized = randomize_runs(rows, seed=7, block="block")

    assert [row["block"] for row in randomized] == ["a", "a", "b", "b"]
    assert {row["run"] for row in randomized[:2]} == {1, 2}
    assert {row["run"] for row in randomized[2:]} == {3, 4}


def test_randomize_runs_raises_for_missing_block_column() -> None:
    """Within-block randomization should fail when block column is not present."""
    rows = [{"run": 1}, {"run": 2}]
    with pytest.raises(ValidationError, match="Block column 'block'"):
        randomize_runs(rows, seed=1, block="block")


def test_generate_doe_returns_summary_and_diagnostics() -> None:
    """One-stop DOE generation should emit design rows and diagnostics payload."""
    result = generate_doe(
        kind="full",
        factors={"a": [0, 1], "b": [2, 3]},
        seed=1,
        randomize=True,
    )

    assert set(result) == {"design", "summary", "interpretation", "warnings"}
    assert result["summary"]["n_runs"] == 4
    assert result["summary"]["design_kind"] == "full_factorial"


def test_generate_doe_supports_replicates_and_center_points() -> None:
    """One-stop DOE generation should expand rows by replicates and center points."""
    result = generate_doe(
        kind="full",
        factors={"a": [0, 1], "b": [2, 3]},
        seed=1,
        replicates=2,
        center_points=2,
        randomize=False,
    )
    # base 4 * replicates 2 + center points 2
    assert result["summary"]["n_runs"] == 10


def test_build_design_supports_latin_hypercube_kind(tmp_path) -> None:
    """Study design builder should support latin-hypercube condition materialization."""
    study = make_study(
        tmp_path=tmp_path,
        study_id="lhs-study",
        factors=(
            Factor(
                name="x",
                description="X",
                kind=FactorKind.MANIPULATED,
                levels=(Level(name="low", value=0.0), Level(name="high", value=1.0)),
            ),
            Factor(
                name="y",
                description="Y",
                kind=FactorKind.MANIPULATED,
                levels=(Level(name="low", value=10.0), Level(name="high", value=20.0)),
            ),
        ),
        design_spec={"kind": "lhs", "n_samples": 5, "randomize": True},
    )

    conditions = build_design(study)

    assert len(conditions) == 5
    assert all("x" in condition.factor_assignments for condition in conditions)
    assert all("y" in condition.factor_assignments for condition in conditions)


def test_build_design_supports_fractional_two_level_kind(tmp_path) -> None:
    """Study design builder should support fractional 2-level condition materialization."""
    study = make_study(
        tmp_path=tmp_path,
        study_id="frac-study",
        factors=(
            Factor("a", "A", levels=(Level("low", 0), Level("high", 1))),
            Factor("b", "B", levels=(Level("low", 0), Level("high", 1))),
            Factor("c", "C", levels=(Level("low", 0), Level("high", 1))),
            Factor("d", "D", levels=(Level("low", 0), Level("high", 1))),
        ),
        design_spec={"kind": "frac2", "randomize": False},
    )

    conditions = build_design(study)

    assert len(conditions) == 8
    for condition in conditions:
        assert set(condition.factor_assignments) == {"a", "b", "c", "d"}
