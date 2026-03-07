"""Hypothesis and analysis-plan schemas."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, cast

from .schemas import ValidationError


class HypothesisKind(StrEnum):
    """Supported research-claim classes."""

    EFFECT = "effect"
    MODERATION = "moderation"
    MEDIATION = "mediation"
    EQUIVALENCE = "equivalence"
    ROBUSTNESS = "robustness"
    EXPLORATORY = "exploratory"


class HypothesisDirection(StrEnum):
    """Expected relationship direction for a hypothesis."""

    GREATER = "greater"
    LESS = "less"
    DIFFERENT = "different"
    EQUIVALENT = "equivalent"


@dataclass(slots=True)
class Contrast:
    """Structured contrast specification for one hypothesis."""

    label: str
    left: str
    right: str
    operation: str = "difference"


@dataclass(slots=True)
class Moderator:
    """Moderator field linked to a hypothesis."""

    name: str
    levels: tuple[str, ...] = ()


@dataclass(slots=True)
class Mediator:
    """Mediator field linked to a hypothesis."""

    name: str
    description: str = ""


@dataclass(slots=True)
class OutcomeSpec:
    """Outcome definition mapped to source tables and derivations."""

    name: str
    source_table: str
    column: str
    aggregation: str
    derivation: str | None = None
    primary: bool = False
    expected_type: str = "float"
    missing_data_policy: str = "drop"
    description: str = ""

    def __post_init__(self) -> None:
        """Validate required outcome properties."""
        if not self.name.strip():
            raise ValidationError("OutcomeSpec.name must be non-empty.")
        if not self.source_table.strip():
            raise ValidationError("OutcomeSpec.source_table must be non-empty.")
        if not self.column.strip():
            raise ValidationError("OutcomeSpec.column must be non-empty.")


@dataclass(slots=True)
class Hypothesis:
    """Machine-readable research claim."""

    hypothesis_id: str
    label: str
    statement: str
    kind: HypothesisKind = HypothesisKind.EFFECT
    independent_vars: tuple[str, ...] = ()
    dependent_vars: tuple[str, ...] = ()
    moderators: tuple[Moderator, ...] = ()
    mediators: tuple[Mediator, ...] = ()
    contrast: Contrast | None = None
    direction: HypothesisDirection = HypothesisDirection.DIFFERENT
    minimum_effect_of_interest: float | None = None
    linked_analysis_plan_id: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate hypothesis shape."""
        if not self.hypothesis_id.strip():
            raise ValidationError("Hypothesis.hypothesis_id must be non-empty.")
        if not self.label.strip():
            raise ValidationError("Hypothesis.label must be non-empty.")
        if not self.statement.strip():
            raise ValidationError("Hypothesis.statement must be non-empty.")


@dataclass(slots=True)
class AnalysisPlan:
    """Mapping from hypotheses to downstream analyses."""

    analysis_plan_id: str
    hypothesis_ids: tuple[str, ...]
    tests: tuple[str, ...]
    outcomes: tuple[str, ...] = ()
    covariates: tuple[str, ...] = ()
    random_effects: tuple[str, ...] = ()
    filters: dict[str, Any] = field(default_factory=dict)
    multiple_comparison_policy: str = "none"
    plots: tuple[str, ...] = ()
    export_tables: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate analysis plan requirements."""
        if not self.analysis_plan_id.strip():
            raise ValidationError("AnalysisPlan.analysis_plan_id must be non-empty.")
        if not self.hypothesis_ids:
            raise ValidationError(
                "AnalysisPlan.hypothesis_ids must contain at least one hypothesis ID."
            )
        if not self.tests:
            raise ValidationError("AnalysisPlan.tests must contain at least one test family.")


def validate_hypothesis_bindings(
    hypotheses: Sequence[Hypothesis],
    *,
    factor_names: Sequence[str],
    outcome_names: Sequence[str],
    analysis_plan_ids: Sequence[str],
) -> list[str]:
    """Validate references from hypotheses to factors, outcomes, and analysis plans."""
    errors: list[str] = []
    factor_name_set = set(factor_names)
    outcome_name_set = set(outcome_names)
    analysis_plan_id_set = set(analysis_plan_ids)

    for hypothesis in hypotheses:
        for variable in hypothesis.independent_vars:
            if variable not in factor_name_set:
                errors.append(
                    "Hypothesis "
                    f"'{hypothesis.hypothesis_id}' references unknown independent variable "
                    f"'{variable}'."
                )
        for variable in hypothesis.dependent_vars:
            if variable not in outcome_name_set:
                errors.append(
                    "Hypothesis "
                    f"'{hypothesis.hypothesis_id}' references unknown dependent variable "
                    f"'{variable}'."
                )

        if (
            hypothesis.linked_analysis_plan_id is not None
            and hypothesis.linked_analysis_plan_id not in analysis_plan_id_set
        ):
            errors.append(
                f"Hypothesis '{hypothesis.hypothesis_id}' references unknown analysis plan "
                f"'{hypothesis.linked_analysis_plan_id}'."
            )

    return errors


def coerce_hypothesis(value: Hypothesis | Mapping[str, Any]) -> Hypothesis:
    """Coerce a mapping payload into a `Hypothesis` instance."""
    if isinstance(value, Hypothesis):
        return value

    mapping = value
    moderators = tuple(
        moderator
        if isinstance(moderator, Moderator)
        else Moderator(
            name=str(cast(Mapping[str, Any], moderator)["name"]),
            levels=tuple(cast(Sequence[str], cast(Mapping[str, Any], moderator).get("levels", ()))),
        )
        for moderator in cast(Sequence[Any], mapping.get("moderators", ()))
    )

    mediators = tuple(
        mediator
        if isinstance(mediator, Mediator)
        else Mediator(
            name=str(cast(Mapping[str, Any], mediator)["name"]),
            description=str(cast(Mapping[str, Any], mediator).get("description", "")),
        )
        for mediator in cast(Sequence[Any], mapping.get("mediators", ()))
    )

    contrast_payload = mapping.get("contrast")
    contrast = None
    if contrast_payload is not None:
        if isinstance(contrast_payload, Contrast):
            contrast = contrast_payload
        else:
            contrast_mapping = cast(Mapping[str, Any], contrast_payload)
            contrast = Contrast(
                label=str(contrast_mapping.get("label", "contrast")),
                left=str(contrast_mapping["left"]),
                right=str(contrast_mapping["right"]),
                operation=str(contrast_mapping.get("operation", "difference")),
            )

    return Hypothesis(
        hypothesis_id=str(mapping["hypothesis_id"]),
        label=str(mapping.get("label", "")),
        statement=str(mapping.get("statement", "")),
        kind=HypothesisKind(str(mapping.get("kind", HypothesisKind.EFFECT.value))),
        independent_vars=tuple(cast(Sequence[str], mapping.get("independent_vars", ()))),
        dependent_vars=tuple(cast(Sequence[str], mapping.get("dependent_vars", ()))),
        moderators=moderators,
        mediators=mediators,
        contrast=contrast,
        direction=HypothesisDirection(
            str(mapping.get("direction", HypothesisDirection.DIFFERENT.value))
        ),
        minimum_effect_of_interest=cast(float | None, mapping.get("minimum_effect_of_interest")),
        linked_analysis_plan_id=cast(str | None, mapping.get("linked_analysis_plan_id")),
        notes=str(mapping.get("notes", "")),
    )


def coerce_outcome(value: OutcomeSpec | Mapping[str, Any]) -> OutcomeSpec:
    """Coerce a mapping payload into an `OutcomeSpec` instance."""
    if isinstance(value, OutcomeSpec):
        return value

    mapping = value
    return OutcomeSpec(
        name=str(mapping["name"]),
        source_table=str(mapping["source_table"]),
        column=str(mapping["column"]),
        aggregation=str(mapping["aggregation"]),
        derivation=cast(str | None, mapping.get("derivation")),
        primary=bool(mapping.get("primary", False)),
        expected_type=str(mapping.get("expected_type", "float")),
        missing_data_policy=str(mapping.get("missing_data_policy", "drop")),
        description=str(mapping.get("description", "")),
    )


def coerce_analysis_plan(value: AnalysisPlan | Mapping[str, Any]) -> AnalysisPlan:
    """Coerce a mapping payload into an `AnalysisPlan` instance."""
    if isinstance(value, AnalysisPlan):
        return value

    mapping = value
    return AnalysisPlan(
        analysis_plan_id=str(mapping["analysis_plan_id"]),
        hypothesis_ids=tuple(cast(Sequence[str], mapping.get("hypothesis_ids", ()))),
        tests=tuple(cast(Sequence[str], mapping.get("tests", ()))),
        outcomes=tuple(cast(Sequence[str], mapping.get("outcomes", ()))),
        covariates=tuple(cast(Sequence[str], mapping.get("covariates", ()))),
        random_effects=tuple(cast(Sequence[str], mapping.get("random_effects", ()))),
        filters=dict(cast(Mapping[str, Any], mapping.get("filters", {}))),
        multiple_comparison_policy=str(mapping.get("multiple_comparison_policy", "none")),
        plots=tuple(cast(Sequence[str], mapping.get("plots", ()))),
        export_tables=tuple(cast(Sequence[str], mapping.get("export_tables", ()))),
        notes=str(mapping.get("notes", "")),
    )
