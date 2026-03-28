"""Top-level study models and validation helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from .conditions import Constraint, Factor, FactorKind, Level
from .hypotheses import (
    AnalysisPlan,
    Hypothesis,
    OutcomeSpec,
    coerce_analysis_plan,
    coerce_hypothesis,
    coerce_outcome,
    validate_hypothesis_bindings,
)
from .io import json_io, yaml_io
from .schemas import (
    SCHEMA_VERSION,
    ProvenanceMetadata,
    RunBudget,
    RunStatus,
    SeedPolicy,
    ValidationError,
    to_jsonable,
)

STUDY_SCHEMA_VERSION = SCHEMA_VERSION


@dataclass(slots=True)
class Block:
    """Blocking structure for design-of-experiments materialization."""

    name: str
    levels: tuple[Any, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate block content."""
        if not self.name.strip():
            raise ValidationError("Block.name must be non-empty.")
        if not self.levels:
            raise ValidationError(f"Block '{self.name}' must contain at least one level.")


@dataclass(slots=True)
class RunSpec:
    """One executable run specification."""

    run_id: str
    study_id: str
    condition_id: str
    problem_id: str
    replicate: int
    seed: int
    agent_spec_ref: Any
    problem_spec_ref: Any
    execution_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RunResult:
    """Normalized result bundle for one run."""

    run_id: str
    status: RunStatus
    outputs: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    evaluator_outputs: list[dict[str, Any]] = field(default_factory=list)
    cost: float = 0.0
    latency: float = 0.0
    trace_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    error_info: str | None = None
    provenance_info: dict[str, Any] = field(default_factory=dict)
    observations: list[Any] = field(default_factory=list)
    run_spec: RunSpec | None = None
    started_at: str | None = None
    ended_at: str | None = None


@dataclass(slots=True)
class Study:
    """Top-level experiment definition."""

    study_id: str
    title: str
    description: str
    authors: tuple[str, ...] = ()
    rationale: str = ""
    tags: tuple[str, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()
    factors: tuple[Factor, ...] = ()
    blocks: tuple[Block, ...] = ()
    constraints: tuple[Constraint, ...] = ()
    design_spec: dict[str, Any] = field(default_factory=lambda: {"kind": "full_factorial"})
    outcomes: tuple[OutcomeSpec, ...] = ()
    analysis_plans: tuple[AnalysisPlan, ...] = ()
    run_budget: RunBudget = field(default_factory=RunBudget)
    seed_policy: SeedPolicy = field(default_factory=SeedPolicy)
    output_dir: Path | None = None
    provenance_metadata: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    problem_ids: tuple[str, ...] = ()
    agent_specs: tuple[str, ...] = ()
    primary_outcomes: tuple[str, ...] = ()
    secondary_outcomes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate basic study fields and normalize output directory."""
        if not self.study_id.strip():
            raise ValidationError("Study.study_id must be non-empty.")
        if not self.title.strip():
            raise ValidationError("Study.title must be non-empty.")
        if self.output_dir is None:
            self.output_dir = Path("artifacts") / self.study_id

    def to_dict(self) -> dict[str, Any]:
        """Serialize the study to a stable JSON/YAML-friendly mapping."""
        payload = cast(dict[str, Any], to_jsonable(self))
        return {"schema_version": STUDY_SCHEMA_VERSION, **payload}

    def to_yaml(self, path: str | Path) -> Path:
        """Write the study definition to YAML."""
        return yaml_io.write_yaml(Path(path), self.to_dict())

    def to_json(self, path: str | Path) -> Path:
        """Write the study definition to JSON."""
        return json_io.write_json(Path(path), self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Study:
        """Construct a study from a loose mapping payload."""
        factors = tuple(
            _coerce_factor(factor) for factor in cast(Sequence[Any], payload.get("factors", ()))
        )
        blocks = tuple(
            _coerce_block(block) for block in cast(Sequence[Any], payload.get("blocks", ()))
        )
        constraints = tuple(
            _coerce_constraint(constraint)
            for constraint in cast(Sequence[Any], payload.get("constraints", ()))
        )

        hypotheses = tuple(
            coerce_hypothesis(hypothesis)
            for hypothesis in cast(Sequence[Any], payload.get("hypotheses", ()))
        )
        outcomes = tuple(
            coerce_outcome(outcome) for outcome in cast(Sequence[Any], payload.get("outcomes", ()))
        )
        analysis_plans = tuple(
            coerce_analysis_plan(plan)
            for plan in cast(Sequence[Any], payload.get("analysis_plans", ()))
        )

        run_budget_payload = payload.get("run_budget")
        run_budget = (
            run_budget_payload
            if isinstance(run_budget_payload, RunBudget)
            else RunBudget(**cast(dict[str, Any], run_budget_payload or {}))
        )

        seed_policy_payload = payload.get("seed_policy")
        seed_policy = (
            seed_policy_payload
            if isinstance(seed_policy_payload, SeedPolicy)
            else SeedPolicy(**cast(dict[str, Any], seed_policy_payload or {}))
        )

        output_dir_payload = payload.get("output_dir")
        output_dir = Path(str(output_dir_payload)) if output_dir_payload else None

        return cls(
            study_id=str(payload["study_id"]),
            title=str(payload.get("title", "")),
            description=str(payload.get("description", "")),
            authors=tuple(cast(Sequence[str], payload.get("authors", ()))),
            rationale=str(payload.get("rationale", "")),
            tags=tuple(cast(Sequence[str], payload.get("tags", ()))),
            hypotheses=hypotheses,
            factors=factors,
            blocks=blocks,
            constraints=constraints,
            design_spec=dict(cast(Mapping[str, Any], payload.get("design_spec", {}))),
            outcomes=outcomes,
            analysis_plans=analysis_plans,
            run_budget=run_budget,
            seed_policy=seed_policy,
            output_dir=output_dir,
            provenance_metadata=dict(
                cast(Mapping[str, Any], payload.get("provenance_metadata", {}))
            ),
            notes=str(payload.get("notes", "")),
            problem_ids=tuple(cast(Sequence[str], payload.get("problem_ids", ()))),
            agent_specs=tuple(cast(Sequence[str], payload.get("agent_specs", ()))),
            primary_outcomes=tuple(cast(Sequence[str], payload.get("primary_outcomes", ()))),
            secondary_outcomes=tuple(cast(Sequence[str], payload.get("secondary_outcomes", ()))),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> Study:
        """Load a study from YAML."""
        return cls.from_dict(yaml_io.read_yaml(Path(path)))

    @classmethod
    def from_json(cls, path: str | Path) -> Study:
        """Load a study from JSON."""
        return cls.from_dict(json_io.read_json(Path(path)))


def validate_study(study: Study) -> list[str]:
    """Validate cross-object references and study consistency."""
    errors: list[str] = []

    factor_names = [factor.name for factor in study.factors]
    block_names = [block.name for block in study.blocks]
    outcome_names = [outcome.name for outcome in study.outcomes]
    analysis_plan_ids = [plan.analysis_plan_id for plan in study.analysis_plans]
    hypothesis_ids = [hypothesis.hypothesis_id for hypothesis in study.hypotheses]

    errors.extend(_duplicate_errors("factor", factor_names))
    errors.extend(_duplicate_errors("block", block_names))
    errors.extend(_duplicate_errors("outcome", outcome_names))
    errors.extend(_duplicate_errors("analysis plan", analysis_plan_ids))
    errors.extend(_duplicate_errors("hypothesis", hypothesis_ids))

    outcome_name_set = set(outcome_names)
    for outcome_name in study.primary_outcomes:
        if outcome_name not in outcome_name_set:
            errors.append(f"Primary outcome '{outcome_name}' is not defined in outcomes.")

    for outcome_name in study.secondary_outcomes:
        if outcome_name not in outcome_name_set:
            errors.append(f"Secondary outcome '{outcome_name}' is not defined in outcomes.")

    errors.extend(
        validate_hypothesis_bindings(
            study.hypotheses,
            factor_names=factor_names,
            outcome_names=outcome_names,
            analysis_plan_ids=analysis_plan_ids,
        )
    )

    for analysis_plan in study.analysis_plans:
        for hypothesis_id in analysis_plan.hypothesis_ids:
            if hypothesis_id not in set(hypothesis_ids):
                errors.append(
                    "Analysis plan "
                    f"'{analysis_plan.analysis_plan_id}' references unknown hypothesis "
                    f"'{hypothesis_id}'."
                )
        for outcome_name in analysis_plan.outcomes:
            if outcome_name not in outcome_name_set:
                errors.append(
                    f"Analysis plan '{analysis_plan.analysis_plan_id}' references unknown outcome "
                    f"'{outcome_name}'."
                )

    problem_binding_factor = _binding_factor(
        study.factors,
        names=("problem_id", "problem"),
    )
    agent_binding_factor = _binding_factor(
        study.factors,
        names=("agent_id", "agent", "agent_spec"),
    )

    if not study.problem_ids and problem_binding_factor is None:
        errors.append("Study.problem_ids must include at least one problem ID.")

    if study.run_budget.max_runs is not None:
        requested_runs = (
            _binding_count(study.problem_ids, problem_binding_factor)
            * _binding_count(study.agent_specs, agent_binding_factor)
            * study.run_budget.replicates
        )
        if requested_runs > study.run_budget.max_runs:
            errors.append(
                "Run budget max_runs is below the configured problem/agent/replicate plan."
            )

    return errors


def load_study(path: str | Path) -> Study:
    """Load a study from YAML or JSON based on file extension."""
    resolved = Path(path)
    suffix = resolved.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return Study.from_yaml(resolved)
    if suffix == ".json":
        return Study.from_json(resolved)
    raise ValidationError("Study file must end with .yaml/.yml or .json.")


def _duplicate_errors(label: str, names: Sequence[str]) -> list[str]:
    """Return duplicate-name errors for one label class."""
    seen: set[str] = set()
    errors: list[str] = []
    for name in names:
        if name in seen:
            errors.append(f"Duplicate {label} name detected: '{name}'.")
        seen.add(name)
    return errors


def _binding_factor(factors: Sequence[Factor], *, names: Sequence[str]) -> Factor | None:
    """Return the first factor that binds a runtime agent or problem identifier."""
    name_set = set(names)
    for factor in factors:
        if factor.name in name_set:
            return factor
    return None


def _binding_count(values: Sequence[str], factor: Factor | None) -> int:
    """Resolve the effective binding count for max-run validation."""
    if values:
        return len(values)
    if factor is not None:
        return max(1, len(factor.levels))
    return 1


def _coerce_factor(value: Factor | Mapping[str, Any]) -> Factor:
    """Coerce a mapping payload into a `Factor` instance."""
    if isinstance(value, Factor):
        return value

    levels = tuple(
        level
        if isinstance(level, Level)
        else Level(
            name=str(cast(Mapping[str, Any], level)["name"]),
            value=cast(Mapping[str, Any], level).get("value"),
            label=cast(str | None, cast(Mapping[str, Any], level).get("label")),
            metadata=dict(
                cast(Mapping[str, Any], cast(Mapping[str, Any], level).get("metadata", {}))
            ),
        )
        for level in cast(Sequence[Any], value.get("levels", ()))
    )

    return Factor(
        name=str(value["name"]),
        description=str(value.get("description", "")),
        kind=FactorKind(str(value.get("kind", FactorKind.MANIPULATED.value))),
        levels=levels,
        dtype=cast(str | None, value.get("dtype")),
        default=value.get("default"),
        metadata=dict(cast(Mapping[str, Any], value.get("metadata", {}))),
    )


def _coerce_block(value: Block | Mapping[str, Any]) -> Block:
    """Coerce a mapping payload into a `Block` instance."""
    if isinstance(value, Block):
        return value

    return Block(
        name=str(value["name"]),
        levels=tuple(cast(Sequence[Any], value.get("levels", ()))),
        metadata=dict(cast(Mapping[str, Any], value.get("metadata", {}))),
    )


def _coerce_constraint(value: Constraint | Mapping[str, Any]) -> Constraint:
    """Coerce a mapping payload into a `Constraint` instance."""
    if isinstance(value, Constraint):
        return value

    return Constraint(
        constraint_id=str(value["constraint_id"]),
        description=str(value.get("description", "")),
        expression=cast(str | None, value.get("expression")),
        callable_ref=cast(str | None, value.get("callable_ref")),
        severity=value.get("severity", "error"),
    )


def build_default_provenance() -> dict[str, Any]:
    """Capture a baseline provenance payload for study manifests."""
    return cast(
        dict[str, Any],
        to_jsonable(
            ProvenanceMetadata.capture(
                package_names=(
                    "design-research-experiments",
                    "design-research-agents",
                    "design-research-problems",
                    "design-research-analysis",
                )
            )
        ),
    )
