"""Metric composition and derived metric helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .schemas import Observation


@dataclass(slots=True)
class MetricPack:
    """Composable set of metric names grouped under one pack label."""

    name: str
    metric_names: tuple[str, ...] = ()
    derived_names: tuple[str, ...] = ()


@dataclass(slots=True)
class MetricComputation:
    """Normalized metric outputs for one run."""

    metrics: dict[str, Any] = field(default_factory=dict)
    evaluations: list[dict[str, Any]] = field(default_factory=list)


def derive_process_metrics(observations: Sequence[Observation]) -> dict[str, Any]:
    """Compute lightweight process metrics from normalized observations."""
    tool_calls = 0
    step_events = 0
    actor_ids: set[str] = set()

    for observation in observations:
        actor_ids.add(observation.actor_id)
        if observation.event_type == "tool_call":
            tool_calls += 1
        if observation.event_type in {"step", "tool_call", "assistant_output"}:
            step_events += 1

    return {
        "tool_call_count": tool_calls,
        "step_event_count": step_events,
        "unique_actor_count": len(actor_ids),
    }


def compose_metrics(
    *,
    agent_metrics: Mapping[str, Any],
    evaluation_rows: Sequence[Mapping[str, Any]],
    observations: Sequence[Observation],
    latency_s: float,
    cost_usd: float,
) -> dict[str, Any]:
    """Compose final run metrics from agent, evaluator, and process sources."""
    derived = derive_process_metrics(observations)
    metrics: dict[str, Any] = dict(agent_metrics)
    metrics.update(derived)
    metrics["latency_s"] = latency_s
    metrics["cost_usd"] = cost_usd

    input_tokens = _safe_number(agent_metrics.get("input_tokens"), default=0)
    output_tokens = _safe_number(agent_metrics.get("output_tokens"), default=0)
    metrics["input_tokens"] = input_tokens
    metrics["output_tokens"] = output_tokens

    if evaluation_rows:
        first_metric = evaluation_rows[0].get("metric_value")
        metrics.setdefault("primary_outcome", first_metric)

    return metrics


def evaluation_rows_from_mapping(
    *,
    run_id: str,
    evaluator_id: str,
    metrics: Mapping[str, Any],
    notes_json: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Create normalized evaluator rows from a metric mapping."""
    rows: list[dict[str, Any]] = []
    for metric_name, metric_value in metrics.items():
        rows.append(
            {
                "run_id": run_id,
                "evaluator_id": evaluator_id,
                "metric_name": metric_name,
                "metric_value": metric_value,
                "metric_unit": "unitless",
                "aggregation_level": "run",
                "notes_json": dict(notes_json or {}),
            }
        )
    return rows


def _safe_number(value: Any, *, default: float) -> float:
    """Convert a value to float when possible, otherwise return default."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
