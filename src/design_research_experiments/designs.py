"""Design-of-experiments builders and generation utilities."""

from __future__ import annotations

import csv
import itertools
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeGuard

from .conditions import Condition, Factor, counterbalance_conditions, materialize_conditions
from .schemas import ConstraintSeverity, ValidationError, hash_identifier, stable_json_dumps
from .study import Study


class DesignKind(StrEnum):
    """Supported DOE generators for v0.1."""

    FULL_FACTORIAL = "full_factorial"
    CONSTRAINED_FACTORIAL = "constrained_factorial"
    RANDOMIZED_BLOCK = "randomized_block"
    REPEATED_MEASURES = "repeated_measures"
    LATIN_SQUARE = "latin_square"
    CUSTOM_MATRIX = "custom_matrix"
    LATIN_HYPERCUBE = "latin_hypercube"
    FRACTIONAL_FACTORIAL_2LEVEL = "fractional_factorial_2level"


_KIND_ALIASES: dict[str, DesignKind] = {
    "full": DesignKind.FULL_FACTORIAL,
    "full_factorial": DesignKind.FULL_FACTORIAL,
    "constrained_factorial": DesignKind.CONSTRAINED_FACTORIAL,
    "randomized_block": DesignKind.RANDOMIZED_BLOCK,
    "repeated_measures": DesignKind.REPEATED_MEASURES,
    "latin_square": DesignKind.LATIN_SQUARE,
    "custom_matrix": DesignKind.CUSTOM_MATRIX,
    "lhs": DesignKind.LATIN_HYPERCUBE,
    "latin_hypercube": DesignKind.LATIN_HYPERCUBE,
    "frac2": DesignKind.FRACTIONAL_FACTORIAL_2LEVEL,
    "fractional_factorial_2level": DesignKind.FRACTIONAL_FACTORIAL_2LEVEL,
}


@dataclass(slots=True)
class DesignSpec:
    """DOE configuration for study materialization."""

    kind: DesignKind = DesignKind.FULL_FACTORIAL
    replicates: int = 1
    randomize: bool = False
    counterbalance: bool = False
    matrix_path: str | None = None
    n_samples: int | None = None
    center_points: int = 0
    block_randomization_key: str | None = None
    options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate design-spec bounds."""
        if self.replicates < 1:
            raise ValidationError("DesignSpec.replicates must be >= 1.")
        if self.n_samples is not None and self.n_samples < 1:
            raise ValidationError("DesignSpec.n_samples must be >= 1 when provided.")
        if self.center_points < 0:
            raise ValidationError("DesignSpec.center_points must be >= 0.")


def build_design(
    study: Study, design_spec: DesignSpec | Mapping[str, Any] | None = None
) -> list[Condition]:
    """Build study conditions for the configured design."""
    resolved_spec = coerce_design_spec(design_spec or study.design_spec)

    if resolved_spec.kind in {DesignKind.FULL_FACTORIAL, DesignKind.CONSTRAINED_FACTORIAL}:
        return materialize_conditions(
            study,
            seed=study.seed_policy.base_seed,
            randomize=resolved_spec.randomize,
            counterbalance=resolved_spec.counterbalance,
        )

    if resolved_spec.kind == DesignKind.RANDOMIZED_BLOCK:
        return materialize_conditions(
            study,
            seed=study.seed_policy.base_seed,
            randomize=True,
            counterbalance=resolved_spec.counterbalance,
        )

    if resolved_spec.kind == DesignKind.REPEATED_MEASURES:
        conditions = materialize_conditions(
            study,
            seed=study.seed_policy.base_seed,
            randomize=resolved_spec.randomize,
            counterbalance=True,
        )
        for index, condition in enumerate(conditions):
            condition.metadata["within_subject_order"] = index
            condition.metadata["design_kind"] = resolved_spec.kind.value
        return conditions

    if resolved_spec.kind == DesignKind.LATIN_SQUARE:
        return _build_latin_square(study=study, design_spec=resolved_spec)

    if resolved_spec.kind == DesignKind.CUSTOM_MATRIX:
        return _build_custom_matrix(study=study, design_spec=resolved_spec)

    if resolved_spec.kind == DesignKind.LATIN_HYPERCUBE:
        n_samples = resolved_spec.n_samples or int(resolved_spec.options.get("n_samples", 0))
        if n_samples < 1:
            raise ValidationError(
                "Latin-hypercube designs require DesignSpec.n_samples or options['n_samples']."
            )

        bounds = _resolve_lhs_bounds(study=study, options=resolved_spec.options)
        rows = latin_hypercube(
            n_samples=n_samples,
            factors=bounds,
            seed=study.seed_policy.base_seed,
        )
        rows = _repeat_rows(rows, replicates=resolved_spec.replicates)
        rows = append_center_points(rows, center_points=resolved_spec.center_points)
        if resolved_spec.randomize:
            rows = randomize_runs(
                rows,
                seed=study.seed_policy.base_seed,
                block=resolved_spec.block_randomization_key,
            )

        conditions = _build_conditions_from_factor_rows(
            study,
            rows,
            design_kind=resolved_spec.kind.value,
        )
        if resolved_spec.counterbalance:
            conditions = counterbalance_conditions(conditions)
        return conditions

    if resolved_spec.kind == DesignKind.FRACTIONAL_FACTORIAL_2LEVEL:
        resolution = str(resolved_spec.options.get("resolution", "III"))
        coded = fractional_factorial_2level(
            [factor.name for factor in study.factors],
            resolution=resolution,
        )
        rows = _decode_fractional_rows(study=study, coded_rows=coded)
        rows = _repeat_rows(rows, replicates=resolved_spec.replicates)
        rows = append_center_points(rows, center_points=resolved_spec.center_points)
        if resolved_spec.randomize:
            rows = randomize_runs(
                rows,
                seed=study.seed_policy.base_seed,
                block=resolved_spec.block_randomization_key,
            )

        conditions = _build_conditions_from_factor_rows(
            study,
            rows,
            design_kind=resolved_spec.kind.value,
        )
        if resolved_spec.counterbalance:
            conditions = counterbalance_conditions(conditions)
        return conditions

    raise ValidationError(f"Unsupported design kind: {resolved_spec.kind!r}")


def coerce_design_spec(value: DesignSpec | Mapping[str, Any]) -> DesignSpec:
    """Coerce a mapping payload into a ``DesignSpec`` instance."""
    if isinstance(value, DesignSpec):
        return value

    options = dict(value.get("options", {}))
    kind_raw = str(value.get("kind", DesignKind.FULL_FACTORIAL.value))
    return DesignSpec(
        kind=_coerce_design_kind(kind_raw),
        replicates=int(value.get("replicates", 1)),
        randomize=bool(value.get("randomize", False)),
        counterbalance=bool(value.get("counterbalance", False)),
        matrix_path=value.get("matrix_path"),
        n_samples=_coerce_optional_int(value.get("n_samples", options.get("n_samples"))),
        center_points=int(value.get("center_points", options.get("center_points", 0))),
        block_randomization_key=value.get(
            "block_randomization_key", options.get("block_randomization_key")
        ),
        options=options,
    )


def full_factorial(levels: Mapping[str, Sequence[Any]]) -> list[dict[str, Any]]:
    """Generate a full-factorial table from explicit factor levels."""
    factor_names = list(levels)
    if not factor_names:
        return []

    level_lists: list[tuple[Any, ...]] = []
    for name in factor_names:
        values = tuple(levels[name])
        if not values:
            raise ValidationError(f"Factor '{name}' must contain at least one level.")
        level_lists.append(values)

    rows: list[dict[str, Any]] = []
    for combination in itertools.product(*level_lists):
        rows.append(dict(zip(factor_names, combination, strict=True)))
    return rows


def latin_hypercube(
    n_samples: int,
    factors: Mapping[str, tuple[float, float]],
    *,
    seed: int = 0,
) -> list[dict[str, float]]:
    """Generate deterministic Latin-hypercube samples for bounded numeric factors."""
    if n_samples <= 0:
        raise ValidationError("n_samples must be positive.")
    if not factors:
        return []

    rng = random.Random(seed)
    columns: dict[str, list[float]] = {}

    for name, bounds in factors.items():
        low, high = bounds
        if not high > low:
            raise ValidationError(f"Factor '{name}' bounds must satisfy high > low.")

        points: list[float] = []
        for index in range(n_samples):
            start = index / n_samples
            end = (index + 1) / n_samples
            point = start + rng.random() * (end - start)
            points.append(low + point * (high - low))

        rng.shuffle(points)
        columns[name] = points

    rows: list[dict[str, float]] = []
    factor_names = list(columns)
    for row_index in range(n_samples):
        rows.append({name: columns[name][row_index] for name in factor_names})
    return rows


def randomize_runs(
    rows: Sequence[Mapping[str, Any]],
    *,
    seed: int = 0,
    block: str | None = None,
) -> list[dict[str, Any]]:
    """Randomize run order globally or within blocks."""
    copied = [dict(row) for row in rows]
    if len(copied) < 2:
        return copied

    if block is not None:
        if any(block not in row for row in copied):
            raise ValidationError(f"Block column '{block}' not present in all design rows.")

        order: list[Any] = []
        groups: dict[Any, list[dict[str, Any]]] = {}
        for row in copied:
            key = row[block]
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(row)

        randomized_rows: list[dict[str, Any]] = []
        for key in order:
            group_rows = list(groups[key])
            random.Random(seed).shuffle(group_rows)
            randomized_rows.extend(group_rows)
        return randomized_rows

    random.Random(seed).shuffle(copied)
    return copied


def fractional_factorial_2level(
    factors: Sequence[str],
    *,
    resolution: str = "III",
) -> list[dict[str, float]]:
    """Generate a two-level fractional-factorial design with coded ``{-1,+1}`` levels."""
    factor_names = list(factors)
    if resolution != "III":
        raise ValidationError("Only resolution 'III' is currently supported.")
    if len(factor_names) < 2:
        raise ValidationError("At least two factors are required for a factorial design.")

    if len(factor_names) <= 3:
        coded = list(itertools.product((-1.0, 1.0), repeat=len(factor_names)))
        return [dict(zip(factor_names, row, strict=True)) for row in coded]

    if len(factor_names) > 6:
        raise ValidationError(
            "Resolution-III fractional templates currently support between 2 and 6 factors."
        )

    base_rows = list(itertools.product((-1.0, 1.0), repeat=3))
    rows: list[dict[str, float]] = []
    for a, b, c in base_rows:
        values = [a, b, c]
        if len(factor_names) >= 4:
            values.append(a * b * c)
        if len(factor_names) >= 5:
            values.append(a * c)
        if len(factor_names) >= 6:
            values.append(b * c)
        rows.append(dict(zip(factor_names, values[: len(factor_names)], strict=True)))

    return rows


def design_balance_report(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, float]]:
    """Compute a simple per-factor balance report for a design table."""
    report: dict[str, dict[str, float]] = {}
    for column in _discover_columns(rows):
        counts = Counter(row.get(column) for row in rows)
        if not counts:
            continue
        values = list(counts.values())
        ratio = float(max(values) / min(values)) if len(values) > 1 else 1.0
        report[column] = {
            "n_levels": float(len(counts)),
            "max_to_min_ratio": ratio,
        }
    return report


def append_center_points(
    rows: Sequence[Mapping[str, Any]],
    *,
    center_points: int,
) -> list[dict[str, Any]]:
    """Append center points to a design table."""
    copied = [dict(row) for row in rows]
    if center_points <= 0:
        return copied
    if not copied:
        raise ValidationError("Cannot append center points to an empty design.")

    columns = _discover_columns(copied)
    center_row: dict[str, Any] = {}
    for column in columns:
        column_values = [row[column] for row in copied if column in row]
        if not column_values:
            continue

        if all(_is_numeric(value) for value in column_values):
            numeric_values = [float(value) for value in column_values]
            center_row[column] = (min(numeric_values) + max(numeric_values)) / 2.0
            continue

        counts = Counter(column_values)
        max_count = max(counts.values())
        ties = [value for value, count in counts.items() if count == max_count]
        for value in column_values:
            if value in ties:
                center_row[column] = value
                break

    return copied + [dict(center_row) for _ in range(center_points)]


def generate_doe(
    *,
    kind: str,
    factors: Mapping[str, Any],
    n_samples: int | None = None,
    seed: int = 0,
    center_points: int = 0,
    replicates: int = 1,
    randomize: bool = True,
    block_randomization_key: str | None = None,
) -> dict[str, Any]:
    """Generate and summarize a DOE table for migration from drcutils-style workflows."""
    if replicates <= 0:
        raise ValidationError("replicates must be positive.")
    if center_points < 0:
        raise ValidationError("center_points must be non-negative.")

    normalized_kind = kind.strip().lower()
    if normalized_kind == "full":
        normalized_kind = DesignKind.FULL_FACTORIAL.value
    elif normalized_kind == "lhs":
        normalized_kind = DesignKind.LATIN_HYPERCUBE.value
    elif normalized_kind == "frac2":
        normalized_kind = DesignKind.FRACTIONAL_FACTORIAL_2LEVEL.value

    if normalized_kind == DesignKind.FULL_FACTORIAL.value:
        levels = _coerce_full_factorial_levels(factors)
        rows = full_factorial(levels)
    elif normalized_kind == DesignKind.LATIN_HYPERCUBE.value:
        if n_samples is None:
            raise ValidationError("n_samples is required for latin-hypercube DOE generation.")
        bounds = _coerce_lhs_factor_bounds(factors)
        rows = latin_hypercube(n_samples=n_samples, factors=bounds, seed=seed)
    elif normalized_kind == DesignKind.FRACTIONAL_FACTORIAL_2LEVEL.value:
        rows = fractional_factorial_2level(list(factors.keys()))
    else:
        raise ValidationError("kind must be one of: full, lhs, frac2")

    rows = _repeat_rows(rows, replicates=replicates)
    rows = append_center_points(rows, center_points=center_points)
    if randomize:
        rows = randomize_runs(rows, seed=seed, block=block_randomization_key)

    ranges = _numeric_ranges(rows)
    balance = design_balance_report(rows)
    warnings = [
        f"Factor '{name}' appears imbalanced (max/min ratio > 2)."
        for name, stats in balance.items()
        if stats["max_to_min_ratio"] > 2.0
    ]

    factor_columns = _discover_columns(rows)
    summary = {
        "n_runs": len(rows),
        "factors": factor_columns,
        "ranges": ranges,
        "design_kind": normalized_kind,
        "balance": balance,
    }

    interpretation = (
        f"Generated a {normalized_kind} DOE with {len(rows)} runs across "
        f"{len(factor_columns)} factors. The summary includes numeric ranges "
        "and balance diagnostics for quick quality checks."
    )

    return {
        "design": rows,
        "summary": summary,
        "interpretation": interpretation,
        "warnings": warnings,
    }


def _build_latin_square(study: Study, design_spec: DesignSpec) -> list[Condition]:
    """Materialize a latin-square design from three named factors."""
    row_factor_name = str(design_spec.options.get("row_factor", ""))
    column_factor_name = str(design_spec.options.get("column_factor", ""))
    treatment_factor_name = str(design_spec.options.get("treatment_factor", ""))

    if not row_factor_name or not column_factor_name or not treatment_factor_name:
        raise ValidationError(
            "Latin-square design requires options row_factor, column_factor, and treatment_factor."
        )

    factor_by_name = {factor.name: factor for factor in study.factors}
    missing = [
        name
        for name in (row_factor_name, column_factor_name, treatment_factor_name)
        if name not in factor_by_name
    ]
    if missing:
        raise ValidationError(
            f"Latin-square factors are missing from the study: {', '.join(missing)}"
        )

    row_factor = factor_by_name[row_factor_name]
    column_factor = factor_by_name[column_factor_name]
    treatment_factor = factor_by_name[treatment_factor_name]

    row_values = row_factor.iter_values()
    column_values = column_factor.iter_values()
    treatment_values = treatment_factor.iter_values()

    n = len(treatment_values)
    if len(row_values) != n or len(column_values) != n:
        raise ValidationError(
            "Latin-square requires equal cardinality for row, column, and treatment factors."
        )

    conditions: list[Condition] = []
    for row_index, row_value in enumerate(row_values):
        for column_index, column_value in enumerate(column_values):
            treatment_value = treatment_values[(row_index + column_index) % n]
            assignments = {
                row_factor_name: row_value,
                column_factor_name: column_value,
                treatment_factor_name: treatment_value,
            }
            condition = _build_condition_from_matrix_row(
                study=study,
                factor_assignment=assignments,
                block_assignment={},
                metadata={
                    "design_kind": design_spec.kind.value,
                    "latin_square_row": row_index,
                    "latin_square_col": column_index,
                },
            )
            conditions.append(condition)

    return conditions


def _build_custom_matrix(study: Study, design_spec: DesignSpec) -> list[Condition]:
    """Materialize conditions from a custom matrix JSON or CSV file."""
    matrix_path = design_spec.matrix_path or str(design_spec.options.get("matrix_path", ""))
    if not matrix_path:
        raise ValidationError("Custom design matrix requires `matrix_path`.")

    resolved_path = Path(matrix_path)
    if not resolved_path.exists():
        raise ValidationError(f"Custom design matrix file not found: {resolved_path}")

    rows = _read_matrix_rows(resolved_path)
    conditions: list[Condition] = []

    factor_names = {factor.name for factor in study.factors}
    block_names = {block.name for block in study.blocks}

    for row_index, row in enumerate(rows):
        factor_assignment = {key: value for key, value in row.items() if key in factor_names}
        block_assignment = {key: value for key, value in row.items() if key in block_names}
        condition = _build_condition_from_matrix_row(
            study=study,
            factor_assignment=factor_assignment,
            block_assignment=block_assignment,
            metadata={
                "design_kind": design_spec.kind.value,
                "matrix_row": row_index,
            },
        )
        conditions.append(condition)

    return conditions


def _read_matrix_rows(path: Path) -> list[dict[str, Any]]:
    """Load matrix rows from JSON or CSV."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        from .io import json_io

        payload = json_io.read_json(path)
        if not isinstance(payload, list):
            raise ValidationError("Custom matrix JSON must contain a list of row objects.")
        return [dict(row) for row in payload]

    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as file_obj:
            reader = csv.DictReader(file_obj)
            return [dict(row) for row in reader]

    raise ValidationError("Custom matrix format must be .json or .csv.")


def _build_condition_from_matrix_row(
    study: Study,
    factor_assignment: Mapping[str, Any],
    block_assignment: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> Condition:
    """Build one condition row while enforcing study constraints."""
    messages: list[str] = []
    admissible = True

    for constraint in study.constraints:
        if constraint.evaluate(factor_assignment, block_assignment):
            continue
        messages.append(f"{constraint.constraint_id}: {constraint.description}")
        if constraint.severity == ConstraintSeverity.ERROR:
            admissible = False

    condition_id = hash_identifier(
        "cond",
        {
            "factors": dict(factor_assignment),
            "blocks": dict(block_assignment),
            "metadata": dict(metadata),
        },
    )

    return Condition(
        condition_id=condition_id,
        factor_assignments=dict(factor_assignment),
        block_assignments=dict(block_assignment),
        metadata={
            **dict(metadata),
            "fingerprint": stable_json_dumps(
                {
                    "factors": dict(factor_assignment),
                    "blocks": dict(block_assignment),
                }
            ),
        },
        admissible=admissible,
        constraint_messages=messages,
    )


def _build_conditions_from_factor_rows(
    study: Study,
    rows: Sequence[Mapping[str, Any]],
    *,
    design_kind: str,
) -> list[Condition]:
    """Convert factor-assignment rows into conditions, including block expansions."""
    block_names = [block.name for block in study.blocks]
    block_levels = [tuple(block.levels) for block in study.blocks]

    block_assignments: list[dict[str, Any]] = [{}]
    if block_levels:
        block_assignments = [
            dict(zip(block_names, combo, strict=True)) for combo in itertools.product(*block_levels)
        ]

    conditions: list[Condition] = []
    for row_index, row in enumerate(rows):
        factor_assignment = dict(row)
        for block_assignment in block_assignments:
            condition = _build_condition_from_matrix_row(
                study=study,
                factor_assignment=factor_assignment,
                block_assignment=block_assignment,
                metadata={
                    "design_kind": design_kind,
                    "row_index": row_index,
                },
            )
            conditions.append(condition)

    return conditions


def _resolve_lhs_bounds(study: Study, options: Mapping[str, Any]) -> dict[str, tuple[float, float]]:
    """Resolve latin-hypercube bounds from factor definitions or explicit options."""
    explicit_bounds_raw = options.get("bounds")
    if explicit_bounds_raw is not None:
        if not isinstance(explicit_bounds_raw, Mapping):
            raise ValidationError("options['bounds'] must be a mapping of factor to [low, high].")
        return _coerce_lhs_factor_bounds(explicit_bounds_raw)

    bounds: dict[str, tuple[float, float]] = {}
    for factor in study.factors:
        values = factor.iter_values()
        if len(values) < 2 or not all(_is_numeric(value) for value in values):
            raise ValidationError(
                "Latin-hypercube study factors must be numeric and provide at least two levels, "
                f"or set design_spec.options['bounds']. Problem factor: '{factor.name}'."
            )

        numeric_values = [float(value) for value in values]
        bounds[factor.name] = (min(numeric_values), max(numeric_values))

    return bounds


def _decode_fractional_rows(
    *,
    study: Study,
    coded_rows: Sequence[Mapping[str, float]],
) -> list[dict[str, Any]]:
    """Map coded fractional-factorial levels to study factor level values."""
    by_name: dict[str, Factor] = {factor.name: factor for factor in study.factors}
    decoded_rows: list[dict[str, Any]] = []

    for coded_row in coded_rows:
        decoded_row: dict[str, Any] = {}
        for name, coded_value in coded_row.items():
            factor = by_name[name]
            if len(factor.levels) != 2:
                raise ValidationError(
                    "Fractional 2-level study designs require exactly two levels per factor. "
                    f"Factor '{name}' has {len(factor.levels)} levels."
                )

            low_value = factor.levels[0].value
            high_value = factor.levels[1].value
            decoded_row[name] = low_value if float(coded_value) < 0 else high_value
        decoded_rows.append(decoded_row)

    return decoded_rows


def _coerce_design_kind(value: str) -> DesignKind:
    """Resolve aliases to one supported design kind."""
    normalized = value.strip().lower()
    if normalized not in _KIND_ALIASES:
        raise ValidationError(f"Unsupported design kind: {value!r}")
    return _KIND_ALIASES[normalized]


def _coerce_optional_int(value: Any) -> int | None:
    """Coerce an optional integer payload value."""
    if value is None:
        return None
    return int(value)


def _coerce_full_factorial_levels(factors: Mapping[str, Any]) -> dict[str, tuple[Any, ...]]:
    """Normalize full-factorial factor specifications."""
    normalized: dict[str, tuple[Any, ...]] = {}
    for name, value in factors.items():
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise ValidationError(
                "Full-factorial factor definitions must be list-like sequences of levels. "
                f"Factor '{name}' is invalid."
            )
        levels = tuple(value)
        if not levels:
            raise ValidationError(f"Factor '{name}' must contain at least one level.")
        normalized[str(name)] = levels
    return normalized


def _coerce_lhs_factor_bounds(factors: Mapping[str, Any]) -> dict[str, tuple[float, float]]:
    """Normalize latin-hypercube factor bounds."""
    bounds: dict[str, tuple[float, float]] = {}
    for name, value in factors.items():
        if (
            not isinstance(value, Sequence)
            or isinstance(value, (str, bytes))
            or len(value) != 2
            or not _is_numeric(value[0])
            or not _is_numeric(value[1])
        ):
            raise ValidationError(
                "Latin-hypercube factor definitions must be [low, high] numeric bounds. "
                f"Factor '{name}' is invalid."
            )

        low = float(value[0])
        high = float(value[1])
        bounds[str(name)] = (low, high)
    return bounds


def _discover_columns(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """Discover columns in first-seen order across row mappings."""
    seen: set[str] = set()
    columns: list[str] = []
    for row in rows:
        for key in row:
            key_str = str(key)
            if key_str in seen:
                continue
            seen.add(key_str)
            columns.append(key_str)
    return columns


def _repeat_rows(rows: Sequence[Mapping[str, Any]], *, replicates: int) -> list[dict[str, Any]]:
    """Repeat all rows a fixed number of times."""
    repeated: list[dict[str, Any]] = []
    for _ in range(replicates):
        repeated.extend(dict(row) for row in rows)
    return repeated


def _numeric_ranges(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[float]]:
    """Return numeric min/max ranges per column."""
    ranges: dict[str, list[float]] = {}
    for column in _discover_columns(rows):
        values = [row.get(column) for row in rows if column in row]
        numeric_values = [float(value) for value in values if _is_numeric(value)]
        if len(numeric_values) != len(values) or not numeric_values:
            continue
        ranges[column] = [min(numeric_values), max(numeric_values)]
    return ranges


def _is_numeric(value: Any) -> TypeGuard[int | float]:
    """Return whether a value is a numeric scalar for DOE range calculations."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


__all__ = [
    "DesignKind",
    "DesignSpec",
    "append_center_points",
    "build_design",
    "coerce_design_spec",
    "design_balance_report",
    "fractional_factorial_2level",
    "full_factorial",
    "generate_doe",
    "latin_hypercube",
    "randomize_runs",
]
