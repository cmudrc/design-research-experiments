"""Additional tests for condition materialization and DOE builders."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from design_research_experiments.conditions import (
    Constraint,
    ConstraintSeverity,
    Factor,
    FactorKind,
    Level,
    balanced_randomization_schedule,
    counterbalance_conditions,
    evaluate_constraint_expression,
    materialize_conditions,
)
from design_research_experiments.designs import (
    DesignKind,
    DesignSpec,
    build_design,
    coerce_design_spec,
)
from design_research_experiments.schemas import ValidationError
from design_research_experiments.study import Block

from .helpers import make_study


def test_condition_expression_engine_and_validation(tmp_path: Path) -> None:
    """Constraint expressions should support safe syntax and reject invalid constructs."""
    context = {
        "x": 2,
        "y": 3,
        "values": [1, 2, 3],
        "obj": {"attr": "ok"},
        "factors": {"mode": "tool"},
    }
    assert evaluate_constraint_expression("x + y == 5", context)
    assert evaluate_constraint_expression("len(values) == 3 and 2 in values", context)
    assert evaluate_constraint_expression("obj.attr == 'ok'", context)
    assert evaluate_constraint_expression("factors['mode'] == 'tool'", context)

    with pytest.raises(ValidationError):
        evaluate_constraint_expression("unknown_name == 1", context)

    with pytest.raises(ValidationError):
        evaluate_constraint_expression("sum(values) > 0", context)

    with pytest.raises(ValidationError):
        evaluate_constraint_expression("int(x=2) == 2", context)

    with pytest.raises(ValidationError):
        evaluate_constraint_expression("1 is 1", context)

    with pytest.raises(ValidationError):
        Factor(name="", description="bad", levels=(Level("l", 1),))

    with pytest.raises(ValidationError):
        Factor(name="bad", description="bad")

    with pytest.raises(ValidationError):
        Constraint(constraint_id="", description="bad", expression="True")

    with pytest.raises(ValidationError):
        Constraint(constraint_id="c", description="bad")

    with pytest.raises(ValidationError):
        DesignSpec(replicates=0)

    with pytest.raises(ValidationError):
        Block(name="", levels=("x",))

    with pytest.raises(ValidationError):
        Block(name="cohort", levels=())


def test_callable_constraints_balancing_and_counterbalance(tmp_path: Path) -> None:
    """Callable constraints and schedule utilities should materialize deterministic outputs."""
    module = types.ModuleType("fake_constraint_module")

    def allow_only_match(factors: dict[str, object], blocks: dict[str, object]) -> bool:
        """Allow only rows where factor and block labels match."""
        return factors.get("mode") == blocks.get("cohort")

    module.allow_only_match = allow_only_match
    sys.modules[module.__name__] = module

    factors = (
        Factor(
            name="mode",
            description="mode",
            kind=FactorKind.MANIPULATED,
            levels=(Level(name="human", value="human"), Level(name="ai", value="ai")),
        ),
    )
    blocks = (Block(name="cohort", levels=("human", "ai")),)
    constraints = (
        Constraint(
            constraint_id="callable",
            description="match mode and cohort",
            callable_ref="fake_constraint_module:allow_only_match",
            severity=ConstraintSeverity.ERROR,
        ),
        Constraint(
            constraint_id="warn",
            description="warning only",
            expression="mode == 'human'",
            severity=ConstraintSeverity.WARNING,
        ),
    )

    conditions = materialize_conditions(
        factors=factors,
        blocks=blocks,
        constraints=constraints,
        randomize=True,
        seed=9,
        counterbalance=True,
    )

    admissible = [condition for condition in conditions if condition.admissible]
    assert len(conditions) == 4
    assert len(admissible) == 2

    schedule = balanced_randomization_schedule(
        [condition.condition_id for condition in conditions], 2, seed=1
    )
    assert len(schedule) == len(conditions) * 2

    assert balanced_randomization_schedule([], 2) == []
    with pytest.raises(ValidationError):
        balanced_randomization_schedule(["c1"], 0)

    assert counterbalance_conditions(conditions[:2]) == conditions[:2]


def test_design_builders_custom_matrix_and_error_paths(tmp_path: Path) -> None:
    """DOE builders should support multiple design kinds and expected errors."""
    study = make_study(tmp_path=tmp_path, study_id="designs-study")

    assert (
        coerce_design_spec(DesignSpec(kind=DesignKind.FULL_FACTORIAL)).kind
        == DesignKind.FULL_FACTORIAL
    )

    randomized = build_design(study, {"kind": "randomized_block", "counterbalance": True})
    repeated = build_design(study, {"kind": "repeated_measures", "randomize": True})
    assert randomized
    assert all("within_subject_order" in condition.metadata for condition in repeated)

    # Custom matrix JSON
    json_matrix = tmp_path / "matrix.json"
    json_matrix.write_text(
        json.dumps(
            [
                {"variant": "a"},
                {"variant": "b"},
            ]
        ),
        encoding="utf-8",
    )
    from_json = build_design(study, {"kind": "custom_matrix", "matrix_path": str(json_matrix)})
    assert len(from_json) == 2

    # Custom matrix CSV
    csv_matrix = tmp_path / "matrix.csv"
    csv_matrix.write_text("variant\na\nb\n", encoding="utf-8")
    from_csv = build_design(study, {"kind": "custom_matrix", "matrix_path": str(csv_matrix)})
    assert len(from_csv) == 2

    bad_matrix = tmp_path / "bad.txt"
    bad_matrix.write_text("variant=a", encoding="utf-8")
    with pytest.raises(ValidationError):
        build_design(study, {"kind": "custom_matrix", "matrix_path": str(bad_matrix)})

    with pytest.raises(ValidationError):
        build_design(study, {"kind": "custom_matrix"})

    with pytest.raises(ValidationError):
        build_design(study, {"kind": "custom_matrix", "matrix_path": str(tmp_path / "missing.csv")})

    with pytest.raises(ValidationError):
        build_design(study, {"kind": "latin_square", "options": {}})

    latin_study = make_study(
        tmp_path=tmp_path,
        study_id="latin-errors",
        factors=(
            Factor(
                name="row",
                description="row",
                levels=(Level("r1", "r1"), Level("r2", "r2")),
            ),
            Factor(
                name="col",
                description="col",
                levels=(Level("c1", "c1"),),
            ),
            Factor(
                name="treat",
                description="treat",
                levels=(Level("t1", "t1"), Level("t2", "t2")),
            ),
        ),
    )

    with pytest.raises(ValidationError):
        build_design(
            latin_study,
            {
                "kind": "latin_square",
                "options": {
                    "row_factor": "row",
                    "column_factor": "missing",
                    "treatment_factor": "treat",
                },
            },
        )

    with pytest.raises(ValidationError):
        build_design(
            latin_study,
            {
                "kind": "latin_square",
                "options": {
                    "row_factor": "row",
                    "column_factor": "col",
                    "treatment_factor": "treat",
                },
            },
        )
