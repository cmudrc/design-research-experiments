"""Factor, level, constraint, and condition materialization primitives."""

from __future__ import annotations

import ast
import itertools
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, cast

from .schemas import (
    ConstraintSeverity,
    ValidationError,
    hash_identifier,
    load_callable,
    stable_json_dumps,
)

if TYPE_CHECKING:
    from .study import Block, Study


class FactorKind(StrEnum):
    """Classification for an experimental factor."""

    MANIPULATED = "manipulated"
    MEASURED = "measured"
    BLOCKED = "blocked"
    NUISANCE = "nuisance"


@dataclass(slots=True)
class Level:
    """One admissible level/value for a factor.

    Args:
        name: Stable level identifier.
        value: Encoded level value.
        label: Optional display label.
        metadata: Optional metadata payload.
    """

    name: str
    value: Any
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalize level content."""
        if not self.name.strip():
            raise ValidationError("Level.name must be non-empty.")
        if self.label is None:
            self.label = self.name


@dataclass(slots=True)
class Factor:
    """Definition of one experimental factor.

    Args:
        name: Stable factor identifier.
        description: Human-readable description.
        kind: Factor type.
        levels: Allowed level set.
        dtype: Optional value type hint.
        default: Optional default level value.
        metadata: Optional metadata payload.
    """

    name: str
    description: str
    kind: FactorKind = FactorKind.MANIPULATED
    levels: tuple[Level, ...] = ()
    dtype: str | None = None
    default: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate factor structure."""
        if not self.name.strip():
            raise ValidationError("Factor.name must be non-empty.")

        if not self.levels and self.default is None:
            raise ValidationError(
                f"Factor '{self.name}' must declare at least one level or a default value."
            )

        level_names = [level.name for level in self.levels]
        if len(level_names) != len(set(level_names)):
            raise ValidationError(f"Factor '{self.name}' has duplicate level names.")

    def iter_values(self) -> tuple[Any, ...]:
        """Return all admissible values for cartesian materialization."""
        if self.levels:
            return tuple(level.value for level in self.levels)
        return (self.default,)


@dataclass(slots=True)
class Constraint:
    """Admissibility rule over factor and block assignments.

    Args:
        constraint_id: Stable identifier for this constraint.
        description: Human-readable description.
        expression: Optional safe expression string.
        callable_ref: Optional `module:callable` reference.
        severity: Whether violation should fail or warn.
    """

    constraint_id: str
    description: str
    expression: str | None = None
    callable_ref: str | None = None
    severity: ConstraintSeverity = ConstraintSeverity.ERROR

    def __post_init__(self) -> None:
        """Validate that a rule implementation is configured."""
        if not self.constraint_id.strip():
            raise ValidationError("Constraint.constraint_id must be non-empty.")
        if self.expression is None and self.callable_ref is None:
            raise ValidationError("Constraint must define either `expression` or `callable_ref`.")

    def evaluate(self, factors: Mapping[str, Any], blocks: Mapping[str, Any]) -> bool:
        """Return whether this constraint passes for one assignment."""
        checks: list[bool] = []

        if self.expression is not None:
            context: dict[str, Any] = {"factors": dict(factors), "blocks": dict(blocks)}
            context.update(factors)
            context.update(blocks)
            checks.append(evaluate_constraint_expression(self.expression, context))

        if self.callable_ref is not None:
            predicate = load_callable(self.callable_ref)
            checks.append(bool(predicate(dict(factors), dict(blocks))))

        return all(checks)


@dataclass(slots=True)
class Condition:
    """One realized treatment combination.

    Args:
        condition_id: Stable condition ID.
        factor_assignments: Materialized factor assignments.
        block_assignments: Materialized block assignments.
        metadata: Optional metadata payload.
        admissible: Constraint admissibility flag.
        constraint_messages: Constraint warning/error messages.
    """

    condition_id: str
    factor_assignments: dict[str, Any]
    block_assignments: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    admissible: bool = True
    constraint_messages: list[str] = field(default_factory=list)


def evaluate_constraint_expression(expression: str, context: Mapping[str, Any]) -> bool:
    """Evaluate one safe boolean expression against an assignment context."""
    parsed = ast.parse(expression, mode="eval")
    evaluated = _eval_ast_node(parsed.body, context)
    if not isinstance(evaluated, bool):
        raise ValidationError("Constraint expression must evaluate to a boolean value.")
    return evaluated


def _eval_ast_node(node: ast.AST, context: Mapping[str, Any]) -> Any:
    """Evaluate a small safe AST subset for constraint expressions."""
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id not in context:
            raise ValidationError(f"Unknown variable '{node.id}' in constraint expression.")
        return context[node.id]

    if isinstance(node, ast.List):
        return [_eval_ast_node(element, context) for element in node.elts]

    if isinstance(node, ast.Tuple):
        return tuple(_eval_ast_node(element, context) for element in node.elts)

    if isinstance(node, ast.Dict):
        keys: list[Any] = []
        for element in node.keys:
            if element is None:
                raise ValidationError("Dictionary unpacking is not allowed in constraints.")
            keys.append(_eval_ast_node(element, context))
        values = [_eval_ast_node(element, context) for element in node.values]
        return dict(zip(keys, values, strict=True))

    if isinstance(node, ast.Attribute):
        base = _eval_ast_node(node.value, context)
        if isinstance(base, Mapping):
            return base.get(node.attr)
        return getattr(base, node.attr)

    if isinstance(node, ast.Subscript):
        target = _eval_ast_node(node.value, context)
        if node.slice is None:
            raise ValidationError("Subscript expressions require an index.")
        index = _eval_ast_node(node.slice, context)
        return target[index]

    if isinstance(node, ast.BoolOp):
        values = [_eval_ast_node(value, context) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(bool(value) for value in values)
        if isinstance(node.op, ast.Or):
            return any(bool(value) for value in values)

    if isinstance(node, ast.UnaryOp):
        operand = _eval_ast_node(node.operand, context)
        if isinstance(node.op, ast.Not):
            return not bool(operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand

    if isinstance(node, ast.BinOp):
        left = _eval_ast_node(node.left, context)
        right = _eval_ast_node(node.right, context)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Mod):
            return left % right

    if isinstance(node, ast.Compare):
        left = _eval_ast_node(node.left, context)
        for operator_node, comparator_node in zip(node.ops, node.comparators, strict=True):
            right = _eval_ast_node(comparator_node, context)
            if not _eval_comparison(operator_node, left, right):
                return False
            left = right
        return True

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValidationError("Only direct function names are allowed in constraints.")
        function_name = node.func.id
        allowed_functions: dict[str, Any] = {
            "len": len,
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
        }
        if function_name not in allowed_functions:
            raise ValidationError(f"Function '{function_name}' is not allowed in constraints.")
        positional_args = [_eval_ast_node(arg, context) for arg in node.args]
        if node.keywords:
            raise ValidationError("Keyword arguments are not allowed in constraint function calls.")
        return allowed_functions[function_name](*positional_args)

    raise ValidationError(f"Unsupported expression node: {type(node).__name__}")


def _eval_comparison(operator_node: ast.AST, left: Any, right: Any) -> bool:
    """Evaluate one comparison operator."""
    if isinstance(operator_node, ast.Eq):
        return bool(left == right)
    if isinstance(operator_node, ast.NotEq):
        return bool(left != right)
    if isinstance(operator_node, ast.Lt):
        return bool(left < right)
    if isinstance(operator_node, ast.LtE):
        return bool(left <= right)
    if isinstance(operator_node, ast.Gt):
        return bool(left > right)
    if isinstance(operator_node, ast.GtE):
        return bool(left >= right)
    if isinstance(operator_node, ast.In):
        return bool(left in right)
    if isinstance(operator_node, ast.NotIn):
        return bool(left not in right)
    raise ValidationError(f"Unsupported comparison operator: {type(operator_node).__name__}")


def materialize_conditions(
    factors: Sequence[Factor] | Study,
    blocks: Sequence[Block] | None = None,
    constraints: Sequence[Constraint] | None = None,
    *,
    seed: int | None = None,
    randomize: bool = False,
    counterbalance: bool = False,
) -> list[Condition]:
    """Materialize admissible conditions from factors, blocks, and constraints."""
    resolved_factors, resolved_blocks, resolved_constraints = _normalize_inputs(
        factors=factors,
        blocks=blocks,
        constraints=constraints,
    )

    factor_names = [factor.name for factor in resolved_factors]
    factor_level_values = [factor.iter_values() for factor in resolved_factors]
    block_names = [block.name for block in resolved_blocks]
    block_values = [tuple(block.levels) for block in resolved_blocks]

    factor_assignments: list[dict[str, Any]] = []
    for combination in itertools.product(*factor_level_values):
        factor_assignments.append(dict(zip(factor_names, combination, strict=True)))

    block_assignments: list[dict[str, Any]] = [{}]
    if block_values:
        block_assignments = []
        for combination in itertools.product(*block_values):
            block_assignments.append(dict(zip(block_names, combination, strict=True)))

    conditions: list[Condition] = []
    for factor_assignment in factor_assignments:
        for block_assignment in block_assignments:
            condition = _build_condition(
                factors=resolved_factors,
                factor_assignment=factor_assignment,
                block_assignment=block_assignment,
                constraints=resolved_constraints,
            )
            conditions.append(condition)

    if counterbalance:
        conditions = counterbalance_conditions(conditions)

    if randomize:
        randomizer = random.Random(seed)
        randomizer.shuffle(conditions)

    return conditions


def balanced_randomization_schedule(
    condition_ids: Sequence[str],
    replicates: int,
    *,
    seed: int | None = None,
) -> list[tuple[str, int, int]]:
    """Create a balanced randomized `(condition_id, replicate, order)` schedule."""
    if replicates < 1:
        raise ValidationError("Replicates must be >= 1.")

    if not condition_ids:
        return []

    randomizer = random.Random(seed)
    base_order = list(condition_ids)
    randomizer.shuffle(base_order)

    schedule: list[tuple[str, int, int]] = []
    for replicate in range(1, replicates + 1):
        rotate_by = (replicate - 1) % len(base_order)
        replicate_order = base_order[rotate_by:] + base_order[:rotate_by]
        for order_index, condition_id in enumerate(replicate_order):
            schedule.append((condition_id, replicate, order_index))

    return schedule


def counterbalance_conditions(conditions: Sequence[Condition]) -> list[Condition]:
    """Apply a simple front/back interleaving for order counterbalancing."""
    ordered = list(conditions)
    if len(ordered) < 3:
        return ordered

    first_half = ordered[::2]
    second_half = ordered[1::2]
    second_half.reverse()
    return first_half + second_half


def _normalize_inputs(
    factors: Sequence[Factor] | Study,
    blocks: Sequence[Block] | None,
    constraints: Sequence[Constraint] | None,
) -> tuple[list[Factor], list[Block], list[Constraint]]:
    """Resolve whether inputs were passed directly or via a `Study` object."""
    from .study import Study

    if isinstance(factors, Study):
        study = factors
        return list(study.factors), list(study.blocks), list(study.constraints)

    return list(factors), list(blocks or ()), list(constraints or ())


def _build_condition(
    *,
    factors: Sequence[Factor],
    factor_assignment: Mapping[str, Any],
    block_assignment: Mapping[str, Any],
    constraints: Sequence[Constraint],
) -> Condition:
    """Build one condition and evaluate all constraints."""
    admissible = True
    messages: list[str] = []

    for constraint in constraints:
        is_valid = constraint.evaluate(factors=factor_assignment, blocks=block_assignment)
        if is_valid:
            continue

        message = f"{constraint.constraint_id}: {constraint.description}"
        messages.append(message)
        if constraint.severity == ConstraintSeverity.ERROR:
            admissible = False

    condition_id = hash_identifier(
        "cond",
        {
            "factors": factor_assignment,
            "blocks": block_assignment,
        },
    )

    return Condition(
        condition_id=condition_id,
        factor_assignments=dict(factor_assignment),
        block_assignments=dict(block_assignment),
        metadata=_build_condition_metadata(
            factors=factors,
            factor_assignment=factor_assignment,
            block_assignment=block_assignment,
        ),
        admissible=admissible,
        constraint_messages=messages,
    )


def _build_condition_metadata(
    *,
    factors: Sequence[Factor],
    factor_assignment: Mapping[str, Any],
    block_assignment: Mapping[str, Any],
) -> dict[str, Any]:
    """Build condition metadata while preserving the stable fingerprint payload."""
    metadata = {
        "fingerprint": stable_json_dumps(
            {
                "factors": factor_assignment,
                "blocks": block_assignment,
            }
        )
    }
    metadata.update(
        _build_comparison_metadata(factors=factors, factor_assignment=factor_assignment)
    )
    return metadata


def _build_comparison_metadata(
    *,
    factors: Sequence[Factor],
    factor_assignment: Mapping[str, Any],
) -> dict[str, Any]:
    """Collect comparison labels and baseline flags from level metadata."""
    comparison_axes: dict[str, dict[str, Any]] = {}
    for factor in factors:
        if factor.name not in factor_assignment:
            continue
        axis = _comparison_axis_for_factor(factor, factor_assignment[factor.name])
        if axis is None:
            continue
        comparison_axes[factor.name] = axis

    if not comparison_axes:
        return {}

    baseline_axes = [name for name, axis in comparison_axes.items() if axis["is_baseline"]]
    labels = [str(axis["label"]) for axis in comparison_axes.values()]
    return {
        "condition_label": " | ".join(labels),
        "comparison_axes": comparison_axes,
        "comparison_baseline": {
            "is_baseline_condition": len(baseline_axes) == len(comparison_axes),
            "axes": baseline_axes,
        },
    }


def _comparison_axis_for_factor(factor: Factor, value: Any) -> dict[str, Any] | None:
    """Return normalized comparison metadata for one factor assignment."""
    for level in factor.levels:
        if level.value != value:
            continue

        if "is_baseline" not in level.metadata and "role" not in level.metadata:
            return None

        is_baseline = bool(
            level.metadata.get("is_baseline", str(level.metadata.get("role", "")) == "baseline")
        )
        role = str(level.metadata.get("role", "baseline" if is_baseline else "treatment"))
        return {
            "value": value,
            "level_name": level.name,
            "label": level.label or level.name,
            "role": role,
            "is_baseline": is_baseline,
        }

    return None


def _coerce_factor(value: Any) -> Factor:
    """Coerce a loose object into a `Factor` instance."""
    if isinstance(value, Factor):
        return value

    mapping = cast(Mapping[str, Any], value)
    levels = tuple(
        level if isinstance(level, Level) else Level(**cast(dict[str, Any], level))
        for level in cast(Sequence[Any], mapping.get("levels", ()))
    )
    return Factor(
        name=str(mapping["name"]),
        description=str(mapping.get("description", "")),
        kind=FactorKind(str(mapping.get("kind", FactorKind.MANIPULATED.value))),
        levels=levels,
        dtype=cast(str | None, mapping.get("dtype")),
        default=mapping.get("default"),
        metadata=dict(cast(Mapping[str, Any], mapping.get("metadata", {}))),
    )
