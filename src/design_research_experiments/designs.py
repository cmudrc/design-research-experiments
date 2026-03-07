"""Design-of-experiments builders."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from .conditions import Condition, materialize_conditions
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


@dataclass(slots=True)
class DesignSpec:
    """DOE configuration for study materialization."""

    kind: DesignKind = DesignKind.FULL_FACTORIAL
    replicates: int = 1
    randomize: bool = False
    counterbalance: bool = False
    matrix_path: str | None = None
    options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate design-spec bounds."""
        if self.replicates < 1:
            raise ValidationError("DesignSpec.replicates must be >= 1.")


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

    raise ValidationError(f"Unsupported design kind: {resolved_spec.kind!r}")


def coerce_design_spec(value: DesignSpec | Mapping[str, Any]) -> DesignSpec:
    """Coerce a mapping payload into a `DesignSpec` instance."""
    if isinstance(value, DesignSpec):
        return value

    return DesignSpec(
        kind=DesignKind(str(value.get("kind", DesignKind.FULL_FACTORIAL.value))),
        replicates=int(value.get("replicates", 1)),
        randomize=bool(value.get("randomize", False)),
        counterbalance=bool(value.get("counterbalance", False)),
        matrix_path=value.get("matrix_path"),
        options=dict(value.get("options", {})),
    )


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
