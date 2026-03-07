"""Problem-layer adapter utilities built on public problem APIs."""

from __future__ import annotations

import importlib
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
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

    if isinstance(problem_spec_ref, str):
        if registry and problem_spec_ref in registry:
            return registry[problem_spec_ref]

        packet = _resolve_from_design_research_problems(problem_spec_ref)
        if packet is not None:
            return packet

        return ProblemPacket(
            problem_id=problem_spec_ref,
            family="unknown",
            brief=problem_spec_ref,
            payload={"problem_id": problem_spec_ref},
            metadata={},
        )

    if isinstance(problem_spec_ref, Mapping):
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

    return _packet_from_object(problem_spec_ref)


def evaluate_problem(
    packet: ProblemPacket,
    run_output: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Execute family-specific evaluation when available and normalize rows."""
    if packet.evaluator is None:
        return []

    raw = packet.evaluator(run_output)
    if isinstance(raw, Mapping):
        return [_normalize_evaluation_row(raw)]
    if isinstance(raw, Sequence):
        rows: list[dict[str, Any]] = []
        for row in raw:
            rows.append(_normalize_evaluation_row(cast(Mapping[str, Any], row)))
        return rows

    return []


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


def _resolve_from_design_research_problems(problem_id: str) -> ProblemPacket | None:
    """Attempt resolving from the upstream design-research-problems package."""
    try:
        module = importlib.import_module("design_research_problems")
    except ImportError:
        return None

    get_problem = getattr(module, "get_problem", None)
    if not callable(get_problem):
        return None

    try:
        problem_obj = get_problem(problem_id)
    except Exception:
        return None

    return _packet_from_object(problem_obj, fallback_problem_id=problem_id)


def _packet_from_object(problem_obj: Any, fallback_problem_id: str | None = None) -> ProblemPacket:
    """Normalize an arbitrary problem-like object into a `ProblemPacket`."""
    problem_id = str(
        getattr(
            problem_obj,
            "problem_id",
            fallback_problem_id if fallback_problem_id is not None else "problem",
        )
    )
    family = str(getattr(problem_obj, "family", problem_obj.__class__.__name__))

    brief_candidate = getattr(problem_obj, "brief", None)
    if brief_candidate is None:
        brief_candidate = getattr(problem_obj, "prompt", None)
    brief = str(brief_candidate) if brief_candidate is not None else problem_id

    evaluator = getattr(problem_obj, "evaluate", None)
    if evaluator is not None and not callable(evaluator):
        raise ValidationError("Problem evaluator must be callable when present.")

    payload = {
        "problem_object": problem_obj,
    }

    metadata = {
        "problem_class": problem_obj.__class__.__name__,
    }

    return ProblemPacket(
        problem_id=problem_id,
        family=family,
        brief=brief,
        payload=payload,
        metadata=metadata,
        evaluator=cast(Callable[[Mapping[str, Any]], Any] | None, evaluator),
    )


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
