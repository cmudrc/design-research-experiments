"""Additional tests for condition materialization and DOE builders."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from design_research_experiments import designs as designs_module
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
        DesignSpec(n_samples=0)

    with pytest.raises(ValidationError):
        DesignSpec(center_points=-1)

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
    with pytest.raises(ValidationError, match="latin_hypercube backend"):
        latin_hypercube(2, {"x": (0.0, 1.0)}, backend="pydoe3")

    assert randomize_runs([{"run": 1}], seed=1) == [{"run": 1}]

    assert len(fractional_factorial_2level(["a", "b"], resolution="III")) == 4
    with pytest.raises(ValidationError, match="Only resolution 'III'"):
        fractional_factorial_2level(["a", "b"], resolution="IV")
    with pytest.raises(ValidationError, match="At least two factors"):
        fractional_factorial_2level(["a"], resolution="III")
    with pytest.raises(ValidationError, match="between 2 and 6 factors"):
        fractional_factorial_2level(["a", "b", "c", "d", "e", "f", "g"], resolution="III")
    with pytest.raises(ValidationError, match="fractional_factorial_2level backend"):
        fractional_factorial_2level(["a", "b"], resolution="III", backend="scipy")

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

    label_only = generate_doe(kind="full", factors={"variant": ["a", "b"]}, randomize=False)
    assert label_only["summary"]["ranges"] == {}

    lhs = generate_doe(
        kind="lhs",
        factors={"x": [0.0, 1.0], "y": [10.0, 20.0]},
        n_samples=2,
        center_points=1,
        replicates=2,
        randomize=True,
        seed=8,
    )
    assert lhs["summary"]["n_runs"] == 5

    frac = generate_doe(kind="frac2", factors={"a": [-1, 1], "b": [-1, 1]}, randomize=False)
    assert frac["summary"]["design_kind"] == DesignKind.FRACTIONAL_FACTORIAL_2LEVEL.value

    with pytest.raises(ValidationError, match="Block column"):
        randomize_runs([{"block": "a"}, {"run": 2}], block="block")
    blocked = randomize_runs(
        [{"block": "a", "run": 1}, {"block": "a", "run": 2}, {"block": "b", "run": 3}],
        block="block",
        seed=3,
    )
    assert [row["block"] for row in blocked] == ["a", "a", "b"]

    bad_json = tmp_path / "matrix-object.json"
    bad_json.write_text(json.dumps({"variant": "a"}), encoding="utf-8")
    study = make_study(tmp_path=tmp_path, study_id="bad-json-study")
    with pytest.raises(ValidationError, match="list of row objects"):
        build_design(study, {"kind": "custom_matrix", "matrix_path": str(bad_json)})

    constrained = make_study(
        tmp_path=tmp_path,
        study_id="constraint-matrix-study",
        constraints=(
            Constraint(
                constraint_id="must-be-b",
                description="variant must be b",
                expression="variant == 'b'",
                severity=ConstraintSeverity.ERROR,
            ),
        ),
    )
    constrained_matrix = tmp_path / "constraint-matrix.json"
    constrained_matrix.write_text(json.dumps([{"variant": "a"}]), encoding="utf-8")
    constrained_conditions = build_design(
        constrained,
        {"kind": "custom_matrix", "matrix_path": str(constrained_matrix)},
    )
    assert constrained_conditions[0].admissible is False
    assert constrained_conditions[0].constraint_messages == ["must-be-b: variant must be b"]


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

    with pytest.raises(ValidationError, match=r"require DesignSpec\.n_samples"):
        build_design(lhs_study, {"kind": "lhs"})

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

    fractional_study = make_study(
        tmp_path=tmp_path,
        study_id="frac-design-study",
        factors=(
            Factor(
                name="a",
                description="A",
                levels=(Level(name="low", value="low"), Level(name="high", value="high")),
            ),
            Factor(
                name="b",
                description="B",
                levels=(Level(name="off", value=False), Level(name="on", value=True)),
            ),
        ),
    )
    fractional_conditions = build_design(
        fractional_study,
        {
            "kind": "frac2",
            "randomize": True,
            "counterbalance": True,
            "center_points": 1,
            "block_randomization_key": "a",
        },
    )
    assert len(fractional_conditions) == 5
    assert {condition.metadata["design_kind"] for condition in fractional_conditions} == {
        DesignKind.FRACTIONAL_FACTORIAL_2LEVEL.value
    }

    latin_mismatch = make_study(
        tmp_path=tmp_path,
        study_id="latin-mismatch-study",
        factors=(
            Factor(
                name="row",
                description="row",
                levels=(Level("r1", "r1"), Level("r2", "r2")),
            ),
            Factor(
                name="col",
                description="col",
                levels=(Level("c1", "c1"), Level("c2", "c2")),
            ),
            Factor(
                name="treat",
                description="treat",
                levels=(Level("t1", "t1"),),
            ),
        ),
    )
    with pytest.raises(ValidationError, match="equal cardinality"):
        build_design(
            latin_mismatch,
            {
                "kind": "latin_square",
                "options": {
                    "row_factor": "row",
                    "column_factor": "col",
                    "treatment_factor": "treat",
                },
            },
        )

    with pytest.raises(ValidationError, match="Unsupported design kind"):
        coerce_design_spec({"kind": "definitely-not-supported"})


def test_optional_doe_backend_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Optional DOE backends should normalize success and missing-dependency failures."""

    class FakeLatinHypercube:
        def __init__(self, *, d: int, seed: int) -> None:
            self.d = d
            self.seed = seed

        def random(self, *, n: int) -> list[list[float]]:
            assert self.d == 2
            assert self.seed == 11
            return [[0.25, 0.75] for _ in range(n)]

    def fake_scale(
        samples: list[list[float]], lows: list[float], highs: list[float]
    ) -> list[list[float]]:
        return [
            [
                low + sample * (high - low)
                for sample, low, high in zip(row, lows, highs, strict=True)
            ]
            for row in samples
        ]

    fake_qmc = SimpleNamespace(LatinHypercube=FakeLatinHypercube, scale=fake_scale)
    monkeypatch.setattr(
        designs_module,
        "import_module",
        lambda name: fake_qmc if name == "scipy.stats.qmc" else SimpleNamespace(),
    )

    scipy_rows = latin_hypercube(
        2,
        {"x": (0.0, 1.0), "y": (10.0, 20.0)},
        seed=11,
        backend="scipy",
    )
    assert scipy_rows == [{"x": 0.25, "y": 17.5}, {"x": 0.25, "y": 17.5}]

    with pytest.raises(ValidationError, match="high > low"):
        latin_hypercube(2, {"x": (1.0, 1.0)}, backend="scipy")

    fake_pydoe = SimpleNamespace(fracfact=lambda generator: [[-1.0, 1.0], [1.0, -1.0]])
    monkeypatch.setattr(
        designs_module,
        "import_module",
        lambda name: fake_pydoe if name == "pyDOE3" else SimpleNamespace(),
    )
    assert fractional_factorial_2level(["a", "b"], backend="pydoe3") == [
        {"a": -1.0, "b": 1.0},
        {"a": 1.0, "b": -1.0},
    ]

    six_factor_rows = fractional_factorial_2level(["a", "b", "c", "d", "e", "f"])
    assert six_factor_rows[0]["e"] == six_factor_rows[0]["a"] * six_factor_rows[0]["c"]
    assert six_factor_rows[0]["f"] == six_factor_rows[0]["b"] * six_factor_rows[0]["c"]

    with pytest.raises(ValidationError, match="between 2 and 6 factors"):
        fractional_factorial_2level(["a", "b", "c", "d", "e", "f", "g"], backend="pydoe3")

    def raise_import_error(name: str) -> None:
        raise ImportError(name)

    monkeypatch.setattr(designs_module, "import_module", raise_import_error)
    with pytest.raises(ValidationError, match="optional dependencies"):
        latin_hypercube(2, {"x": (0.0, 1.0)}, backend="qmc")
    with pytest.raises(ValidationError, match="optional dependencies"):
        fractional_factorial_2level(["a", "b"], backend="pydoe")
