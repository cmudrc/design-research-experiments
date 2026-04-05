"""Problem-layer adapter utilities for orchestration-owned packet handling."""

from __future__ import annotations

import importlib
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, cast

from ..schemas import ValidationError


@dataclass(slots=True)
class ProblemPacket:
    """Normalized executable problem payload."""

    problem_id: str
    family: str
    brief: str
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    evaluator: Callable[[Mapping[str, Any]], Any] | None = None


def resolve_problem(
    problem_spec_ref: Any,
    *,
    registry: Mapping[str, ProblemPacket] | None = None,
) -> ProblemPacket:
    """Resolve a problem reference into a normalized packet."""
    if isinstance(problem_spec_ref, ProblemPacket):
        return problem_spec_ref

    if isinstance(problem_spec_ref, str) and registry and problem_spec_ref in registry:
        return _packet_from_registry_entry(registry[problem_spec_ref])

    if isinstance(problem_spec_ref, Mapping):
        return _packet_from_mapping(problem_spec_ref)

    if isinstance(problem_spec_ref, str):
        owner_integration = _load_problems_integration_module()
        if owner_integration is None:
            raise ValidationError(
                "String problem references now require `design_research_problems.integration`. "
                "Install the coordinated monthly release or pass an explicit `ProblemPacket` "
                "through `problem_registry`."
            )
        binding = owner_integration.resolve_problem_binding(problem_spec_ref)
        return _packet_from_problem_binding(binding, owner_integration=owner_integration)

    raise ValidationError(
        "Standalone design-research-experiments accepts only `ProblemPacket` instances, "
        "explicit packet mappings, or string problem ids resolved through "
        "`design_research_problems.integration`."
    )


def evaluate_problem(
    packet: ProblemPacket,
    run_output: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Execute family-specific evaluation when available and normalize rows."""
    if packet.evaluator is None:
        return []

    evaluator_input = _resolve_evaluator_input(packet, run_output)
    raw = packet.evaluator(evaluator_input)
    return _normalize_evaluation_payload(raw)


def sample_problem_packets(
    problem_refs: Sequence[Any],
    *,
    registry: Mapping[str, ProblemPacket] | None = None,
    sample_size: int | None = None,
    seed: int = 0,
    balanced_by_family: bool = False,
) -> list[ProblemPacket]:
    """Resolve and sample problem packets with optional family balancing."""
    resolved = [resolve_problem(problem_ref, registry=registry) for problem_ref in problem_refs]
    if sample_size is None or sample_size >= len(resolved):
        return resolved

    if not balanced_by_family:
        randomizer = random.Random(seed)
        return randomizer.sample(resolved, sample_size)

    buckets: dict[str, list[ProblemPacket]] = {}
    for packet in resolved:
        buckets.setdefault(packet.family, []).append(packet)

    randomizer = random.Random(seed)
    for bucket in buckets.values():
        randomizer.shuffle(bucket)

    sampled: list[ProblemPacket] = []
    families = sorted(buckets)
    while families and len(sampled) < sample_size:
        next_families: list[str] = []
        for family in families:
            bucket = buckets[family]
            if not bucket:
                continue
            sampled.append(bucket.pop())
            if len(sampled) >= sample_size:
                break
            if bucket:
                next_families.append(family)
        families = next_families

    return sampled


def _packet_from_registry_entry(problem_ref: Any) -> ProblemPacket:
    """Resolve one explicit registry entry into a packet."""
    if isinstance(problem_ref, ProblemPacket):
        return problem_ref
    if isinstance(problem_ref, Mapping):
        return _packet_from_mapping(problem_ref)

    raise ValidationError(
        "Problem registries now require `ProblemPacket` values or explicit packet "
        "mappings. Resolve packaged sibling problems by string id through "
        "`design_research_problems.integration`."
    )


def _packet_from_mapping(problem_spec_ref: Mapping[str, Any]) -> ProblemPacket:
    """Build one packet from an explicit mapping payload."""
    return ProblemPacket(
        problem_id=str(problem_spec_ref.get("problem_id", "problem")),
        family=str(problem_spec_ref.get("family", "unknown")),
        brief=str(problem_spec_ref.get("brief", "")),
        payload=dict(cast(Mapping[str, Any], problem_spec_ref.get("payload", {}))),
        metadata=dict(cast(Mapping[str, Any], problem_spec_ref.get("metadata", {}))),
        evaluator=cast(
            Callable[[Mapping[str, Any]], Any] | None,
            problem_spec_ref.get("evaluator"),
        ),
    )


def _packet_from_problem_binding(binding: Any, *, owner_integration: Any) -> ProblemPacket:
    """Convert one owner-owned `ProblemBinding` into the experiments packet shape."""
    def _evaluate_bound_problem(run_output: Mapping[str, Any]) -> Any:
        return owner_integration.evaluate_problem_output(binding, run_output)

    return ProblemPacket(
        problem_id=str(binding.problem_id),
        family=str(binding.family),
        brief=str(binding.brief),
        payload={"problem_object": binding.problem_object},
        metadata=dict(binding.metadata),
        evaluator=_evaluate_bound_problem,
    )


def _load_problems_integration_module() -> Any | None:
    """Return the packaged problem-integration module when available."""
    try:
        return importlib.import_module("design_research_problems.integration")
    except ImportError as exc:
        try:
            importlib.import_module("design_research_problems")
        except ImportError:
            return None
        raise ValidationError(
            "design-research-problems is installed but does not expose the package-owned "
            "`integration` module. Upgrade to the coordinated monthly release."
        ) from exc


def _resolve_evaluator_input(_packet: ProblemPacket, run_output: Mapping[str, Any]) -> Any:
    """Resolve the best evaluator input for packaged and external problem evaluators."""
    preferred_keys = ("candidate", "state", "answer", "solution", "final_answer", "x")
    for key in preferred_keys:
        if key in run_output:
            return run_output[key]
    return run_output


def _normalize_evaluation_payload(raw: Any) -> list[dict[str, Any]]:
    """Normalize evaluator payloads into canonical experiment evaluation rows."""
    if isinstance(raw, Mapping):
        if _looks_like_evaluation_row(raw):
            return [_normalize_evaluation_row(raw)]
        return _metric_rows_from_mapping(raw)

    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        rows: list[dict[str, Any]] = []
        for row in raw:
            rows.extend(_normalize_evaluation_payload(row))
        return rows

    mapping = _object_to_mapping(raw)
    if mapping is None:
        return []
    return _metric_rows_from_mapping(mapping)


def _looks_like_evaluation_row(row: Mapping[str, Any]) -> bool:
    """Return whether a mapping already resembles one canonical evaluation row."""
    return any(key in row for key in ("metric_name", "metric_value", "value"))


def _metric_rows_from_mapping(metrics: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Expand a metrics mapping into canonical evaluation rows."""
    rows: list[dict[str, Any]] = []
    for metric_name, metric_value in metrics.items():
        if str(metric_name) == "higher_is_better":
            continue
        if not _is_metric_scalar(metric_value):
            continue
        rows.append(
            {
                "evaluator_id": "problem_evaluator",
                "metric_name": str(metric_name),
                "metric_value": metric_value,
                "metric_unit": "unitless",
                "aggregation_level": "run",
                "notes_json": {},
            }
        )
    return rows


def _object_to_mapping(value: Any) -> Mapping[str, Any] | None:
    """Best-effort conversion of an evaluation object to a flat mapping."""
    if value is None:
        return None
    if isinstance(value, Mapping):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return {field_info.name: getattr(value, field_info.name) for field_info in fields(value)}
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            candidate = to_dict()
        except Exception:
            candidate = None
        if isinstance(candidate, Mapping):
            return cast(Mapping[str, Any], candidate)
    if hasattr(value, "__dict__"):
        return cast(Mapping[str, Any], vars(value))
    return None


def _normalize_evaluation_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one evaluator row to canonical shape."""
    return {
        "evaluator_id": str(row.get("evaluator_id", "problem_evaluator")),
        "metric_name": str(row.get("metric_name", "score")),
        "metric_value": row.get("metric_value", row.get("value")),
        "metric_unit": str(row.get("metric_unit", "unitless")),
        "aggregation_level": str(row.get("aggregation_level", "run")),
        "notes_json": row.get("notes_json", {}),
    }


def _is_metric_scalar(value: Any) -> bool:
    """Return whether one value is suitable for scalar metric export."""
    return isinstance(value, bool | int | float)
