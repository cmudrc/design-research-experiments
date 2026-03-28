"""Additional tests for condition materialization and DOE builders."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

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
    append_center_points,
    build_design,
    coerce_design_spec,
    design_balance_report,
    fractional_factorial_2level,
    full_factorial,
    generate_doe,
    latin_hypercube,
    randomize_runs,
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


def test_condition_expression_engine_covers_additional_ast_nodes() -> None:
    """The safe expression evaluator should support the remaining approved AST forms."""
    context = {
        "x": 2,
        "y": 3,
        "values": [1, 2, 3],
        "namespace": SimpleNamespace(attr="ok"),
        "flag": 0,
    }

    assert evaluate_constraint_expression("[x, y] == [2, 3]", context)
    assert evaluate_constraint_expression("(x, y) == (2, 3)", context)
    assert evaluate_constraint_expression("{'answer': x + y}['answer'] == 5", context)
    assert evaluate_constraint_expression("namespace.attr == 'ok'", context)
    assert evaluate_constraint_expression("not False and +x == 2 and -x == -2", context)
    assert evaluate_constraint_expression(
        "x - 1 == 1 and x * y == 6 and y / x == 1.5 and y % x == 1",
        context,
    )
    assert evaluate_constraint_expression("1 < x <= y and x <= 2 and y > 2 and y >= 3", context)
    assert evaluate_constraint_expression("2 in values and 4 not in values", context)
    assert evaluate_constraint_expression("bool(flag) == False or str(x) == '2'", context)

    with pytest.raises(ValidationError, match="must evaluate to a boolean"):
        evaluate_constraint_expression("{'answer': x + y}", context)

    with pytest.raises(ValidationError, match="Dictionary unpacking"):
        evaluate_constraint_expression("{**{'a': 1}} == {'a': 1}", context)

    with pytest.raises(ValidationError, match=r"Level\.name"):
        Level(name="", value=1)

    with pytest.raises(ValidationError, match="duplicate level names"):
        Factor(
            name="duplicate-levels",
            description="bad",
            levels=(Level(name="on", value=True), Level(name="on", value=False)),
        )

    assert Factor(name="with-default", description="default-only", default=True).iter_values() == (
        True,
    )


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


def test_design_helper_functions_cover_error_and_summary_paths(tmp_path: Path) -> None:
    """DOE utility helpers should cover edge validation and summary branches."""
    assert full_factorial({}) == []
    with pytest.raises(ValidationError, match="at least one level"):
        full_factorial({"a": []})

    with pytest.raises(ValidationError, match="n_samples must be positive"):
        latin_hypercube(0, {"x": (0.0, 1.0)})
    assert latin_hypercube(2, {}) == []
    with pytest.raises(ValidationError, match="high > low"):
        latin_hypercube(2, {"x": (1.0, 1.0)})

    assert randomize_runs([{"run": 1}], seed=1) == [{"run": 1}]

    assert len(fractional_factorial_2level(["a", "b"], resolution="III")) == 4
    with pytest.raises(ValidationError, match="Only resolution 'III'"):
        fractional_factorial_2level(["a", "b"], resolution="IV")
    with pytest.raises(ValidationError, match="At least two factors"):
        fractional_factorial_2level(["a"], resolution="III")
    with pytest.raises(ValidationError, match="between 2 and 6 factors"):
        fractional_factorial_2level(["a", "b", "c", "d", "e", "f", "g"], resolution="III")

    assert append_center_points([], center_points=0) == []
    with pytest.raises(ValidationError, match="Cannot append center points"):
        append_center_points([], center_points=1)

    centered = append_center_points(
        [
            {"x": 0.0, "label": "a"},
            {"x": 4.0, "label": "a"},
            {"x": 2.0, "label": "b"},
        ],
        center_points=1,
    )
    assert centered[-1] == {"x": 2.0, "label": "a"}

    balance = design_balance_report([{"variant": "a"}, {"variant": "a"}, {"variant": "b"}])
    assert balance["variant"]["n_levels"] == 2.0
    assert balance["variant"]["max_to_min_ratio"] == 2.0

    imbalanced = generate_doe(
        kind="full",
        factors={"variant": [0, 0, 0, 1]},
        randomize=False,
    )
    assert imbalanced["warnings"] == ["Factor 'variant' appears imbalanced (max/min ratio > 2)."]

    with pytest.raises(ValidationError, match="replicates must be positive"):
        generate_doe(kind="full", factors={"a": [0, 1]}, replicates=0)
    with pytest.raises(ValidationError, match="center_points must be non-negative"):
        generate_doe(kind="full", factors={"a": [0, 1]}, center_points=-1)
    with pytest.raises(ValidationError, match="n_samples is required"):
        generate_doe(kind="lhs", factors={"x": [0.0, 1.0]})
    with pytest.raises(ValidationError, match="kind must be one of"):
        generate_doe(kind="unknown", factors={"a": [0, 1]})
    with pytest.raises(ValidationError, match="Full-factorial factor definitions"):
        generate_doe(kind="full", factors={"a": "bad"})
    with pytest.raises(ValidationError, match="at least one level"):
        generate_doe(kind="full", factors={"a": []})
    with pytest.raises(ValidationError, match="Latin-hypercube factor definitions"):
        generate_doe(kind="lhs", factors={"x": ["low", "high"]}, n_samples=2)

    bad_json = tmp_path / "matrix-object.json"
    bad_json.write_text(json.dumps({"variant": "a"}), encoding="utf-8")
    study = make_study(tmp_path=tmp_path, study_id="bad-json-study")
    with pytest.raises(ValidationError, match="list of row objects"):
        build_design(study, {"kind": "custom_matrix", "matrix_path": str(bad_json)})


def test_build_design_covers_lhs_bounds_and_fractional_validation_paths(tmp_path: Path) -> None:
    """LHS and fractional builders should validate bounds and factor decoding assumptions."""
    lhs_study = make_study(
        tmp_path=tmp_path,
        study_id="lhs-bounds-study",
        factors=(
            Factor(
                name="x",
                description="X",
                levels=(Level(name="low", value=0.0), Level(name="high", value=1.0)),
            ),
            Factor(
                name="y",
                description="Y",
                levels=(Level(name="low", value=10.0), Level(name="high", value=20.0)),
            ),
        ),
        blocks=(Block(name="cohort", levels=("a", "b")),),
    )

    conditions = build_design(
        lhs_study,
        {
            "kind": "lhs",
            "n_samples": 2,
            "counterbalance": True,
            "options": {"bounds": {"x": [1.0, 2.0], "y": [10.0, 20.0]}},
        },
    )
    assert len(conditions) == 4
    assert {condition.block_assignments["cohort"] for condition in conditions} == {"a", "b"}

    with pytest.raises(ValidationError, match="options\\['bounds'\\] must be a mapping"):
        build_design(
            lhs_study,
            {"kind": "lhs", "options": {"n_samples": 1, "bounds": [0.0, 1.0]}},
        )

    non_numeric_lhs = make_study(
        tmp_path=tmp_path,
        study_id="lhs-nonnumeric-study",
        factors=(
            Factor(
                name="label",
                description="Label",
                levels=(Level(name="a", value="a"), Level(name="b", value="b")),
            ),
        ),
    )
    with pytest.raises(ValidationError, match="must be numeric and provide at least two levels"):
        build_design(non_numeric_lhs, {"kind": "lhs", "n_samples": 2})

    invalid_fractional = make_study(
        tmp_path=tmp_path,
        study_id="invalid-frac-study",
        factors=(
            Factor(name="a", description="A", levels=(Level(name="only", value=0),)),
            Factor(
                name="b",
                description="B",
                levels=(Level(name="low", value=0), Level(name="high", value=1)),
            ),
        ),
    )
    with pytest.raises(ValidationError, match="exactly two levels per factor"):
        build_design(invalid_fractional, {"kind": "frac2"})
