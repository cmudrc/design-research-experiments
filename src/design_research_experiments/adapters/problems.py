"""Problem-layer adapter utilities built on public problem APIs."""

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


def _resolve_from_design_research_problems(problem_id: str) -> ProblemPacket | None:
    """Attempt resolving from the upstream design-research-problems package."""
    try:
        module = importlib.import_module("design_research_problems")
        get_problem = getattr(module, "get_problem", None)
    except Exception:
        return None

    if not callable(get_problem):
        return None

    try:
        problem_obj = get_problem(problem_id)
    except Exception:
        return None

    return _packet_from_object(problem_obj, fallback_problem_id=problem_id)


def _packet_from_object(problem_obj: Any, fallback_problem_id: str | None = None) -> ProblemPacket:
    """Normalize an arbitrary problem-like object into a `ProblemPacket`."""
    metadata_object = getattr(problem_obj, "metadata", None)
    problem_id = _stringify_first(
        getattr(metadata_object, "problem_id", None),
        getattr(problem_obj, "problem_id", None),
        fallback_problem_id,
        "problem",
    )
    family = _stringify_first(
        _value_or_enum(getattr(metadata_object, "kind", None)),
        getattr(problem_obj, "family", None),
        problem_obj.__class__.__name__,
    )

    brief = _resolve_problem_brief(problem_obj, fallback=problem_id)

    evaluator = getattr(problem_obj, "evaluate", None)
    if evaluator is not None and not callable(evaluator):
        raise ValidationError("Problem evaluator must be callable when present.")

    payload = {
        "problem_object": problem_obj,
    }

    metadata = {
        "problem_class": problem_obj.__class__.__name__,
    }
    metadata.update(_extract_problem_metadata(problem_obj))

    return ProblemPacket(
        problem_id=problem_id,
        family=family,
        brief=brief,
        payload=payload,
        metadata=metadata,
        evaluator=cast(Callable[[Mapping[str, Any]], Any] | None, evaluator),
    )


def _resolve_problem_brief(problem_obj: Any, *, fallback: str) -> str:
    """Resolve the richest available human-readable brief for a problem object."""
    render_brief = getattr(problem_obj, "render_brief", None)
    if callable(render_brief):
        try:
            rendered = render_brief()
        except TypeError:
            rendered = None
        except Exception:
            rendered = None
        normalized = _normalize_text(rendered)
        if normalized is not None:
            return normalized

    for attribute_name in ("statement_markdown", "brief", "prompt"):
        normalized = _normalize_text(getattr(problem_obj, attribute_name, None))
        if normalized is not None:
            return normalized

    metadata_object = getattr(problem_obj, "metadata", None)
    normalized_summary = _normalize_text(getattr(metadata_object, "summary", None))
    if normalized_summary is not None:
        return normalized_summary
    normalized_title = _normalize_text(getattr(metadata_object, "title", None))
    if normalized_title is not None:
        return normalized_title
    return fallback


def _extract_problem_metadata(problem_obj: Any) -> dict[str, Any]:
    """Extract interoperable metadata from a packaged problem-like object."""
    metadata_object = getattr(problem_obj, "metadata", None)
    metadata: dict[str, Any] = {}

    title = _normalize_text(getattr(metadata_object, "title", None))
    if title is not None:
        metadata["title"] = title

    summary = _normalize_text(getattr(metadata_object, "summary", None))
    if summary is not None:
        metadata["summary"] = summary

    problem_kind = _value_or_enum(getattr(metadata_object, "kind", None))
    normalized_kind = _normalize_text(problem_kind)
    if normalized_kind is not None:
        metadata["problem_kind"] = normalized_kind

    capabilities = _string_sequence(getattr(metadata_object, "capabilities", None))
    if capabilities:
        metadata["capabilities"] = capabilities

    study_suitability = _string_sequence(getattr(metadata_object, "study_suitability", None))
    if study_suitability:
        metadata["study_suitability"] = study_suitability

    feature_flags = _string_sequence(getattr(metadata_object, "feature_flags", None))
    if feature_flags:
        metadata["feature_flags"] = feature_flags

    implementation = _normalize_text(getattr(metadata_object, "implementation", None))
    if implementation is not None:
        metadata["implementation"] = implementation

    return metadata


def _resolve_evaluator_input(packet: ProblemPacket, run_output: Mapping[str, Any]) -> Any:
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
        return {
            field_info.name: getattr(value, field_info.name)
            for field_info in fields(value)
        }
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


def _value_or_enum(value: Any) -> Any:
    """Return an enum's value when present, otherwise the original value."""
    enum_value = getattr(value, "value", None)
    if enum_value is not None:
        return enum_value
    return value


def _stringify_first(*values: Any) -> str:
    """Return the first non-empty stringified value."""
    for value in values:
        normalized = _normalize_text(value)
        if normalized is not None:
            return normalized
    return ""


def _string_sequence(value: Any) -> tuple[str, ...]:
    """Normalize a loose sequence of values to a stable string tuple."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value if _normalize_text(item) is not None)


def _normalize_text(value: Any) -> str | None:
    """Normalize one optional value to non-empty text."""
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _is_metric_scalar(value: Any) -> bool:
    """Return whether one value is suitable for scalar metric export."""
    return isinstance(value, bool | int | float)
