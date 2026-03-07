"""Agent-layer adapter utilities built on public agent APIs."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..conditions import Condition
from ..schemas import Observation, ObservationLevel, ValidationError, hash_identifier, utc_now_iso
from ..study import RunSpec
from .problems import ProblemPacket


@dataclass(slots=True)
class AgentExecution:
    """Normalized agent execution bundle."""

    output: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    events: list[Observation] = field(default_factory=list)
    trace_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def resolve_agent(
    agent_spec_ref: Any,
    *,
    condition: Condition,
    factories: Mapping[str, Callable[[Condition], Any]] | None = None,
) -> Any:
    """Resolve an agent reference into an executable object."""
    if isinstance(agent_spec_ref, str):
        if factories and agent_spec_ref in factories:
            return factories[agent_spec_ref](condition)

        maybe_agent = _resolve_from_design_research_agents(agent_spec_ref)
        if maybe_agent is not None:
            return maybe_agent

        raise ValidationError(
            "Unknown agent spec "
            f"'{agent_spec_ref}'. Register a factory or pass an executable object."
        )

    return agent_spec_ref


def execute_agent(
    *,
    agent_spec_ref: Any,
    run_spec: RunSpec,
    condition: Condition,
    problem_packet: ProblemPacket,
    factories: Mapping[str, Callable[[Condition], Any]] | None = None,
) -> AgentExecution:
    """Execute one agent run and normalize outputs, events, and trace refs."""
    executable = resolve_agent(agent_spec_ref, condition=condition, factories=factories)
    raw = _invoke_agent(
        executable=executable,
        run_spec=run_spec,
        condition=condition,
        problem_packet=problem_packet,
    )
    return _normalize_agent_execution(raw=raw, run_spec=run_spec, condition=condition)


def _resolve_from_design_research_agents(agent_id: str) -> Any | None:
    """Attempt loading a public constructor from design-research-agents."""
    try:
        module = importlib.import_module("design_research_agents")
    except ImportError:
        return None

    if hasattr(module, agent_id):
        constructor = getattr(module, agent_id)
        if callable(constructor):
            try:
                return constructor()
            except Exception:
                return constructor
    return None


def _invoke_agent(
    *,
    executable: Any,
    run_spec: RunSpec,
    condition: Condition,
    problem_packet: ProblemPacket,
) -> Any:
    """Invoke an agent object or callable with a best-effort argument mapping."""
    if hasattr(executable, "run") and callable(executable.run):
        return _invoke_callable(
            callable_obj=executable.run,
            run_spec=run_spec,
            condition=condition,
            problem_packet=problem_packet,
        )

    if callable(executable):
        return _invoke_callable(
            callable_obj=executable,
            run_spec=run_spec,
            condition=condition,
            problem_packet=problem_packet,
        )

    raise ValidationError("Resolved agent object is not executable.")


def _invoke_callable(
    *,
    callable_obj: Callable[..., Any],
    run_spec: RunSpec,
    condition: Condition,
    problem_packet: ProblemPacket,
) -> Any:
    """Invoke a callable by matching supported keyword parameters."""
    parameters = inspect.signature(callable_obj).parameters
    kwargs: dict[str, Any] = {}

    if "problem_packet" in parameters:
        kwargs["problem_packet"] = problem_packet
    if "problem" in parameters:
        kwargs["problem"] = problem_packet
    if "brief" in parameters:
        kwargs["brief"] = problem_packet.brief
    if "run_spec" in parameters:
        kwargs["run_spec"] = run_spec
    if "condition" in parameters:
        kwargs["condition"] = condition
    if "seed" in parameters:
        kwargs["seed"] = run_spec.seed

    if kwargs:
        return callable_obj(**kwargs)

    try:
        return callable_obj(problem_packet, run_spec.seed)
    except TypeError:
        return callable_obj(problem_packet)


def _normalize_agent_execution(
    *,
    raw: Any,
    run_spec: RunSpec,
    condition: Condition,
) -> AgentExecution:
    """Normalize raw execution output to canonical adapter shape."""
    if isinstance(raw, Mapping):
        output = dict(raw.get("output", raw.get("outputs", {})))
        if not output and "text" in raw:
            output = {"text": raw["text"]}

        metrics = dict(raw.get("metrics", {}))
        trace_refs = [str(value) for value in raw.get("trace_refs", [])]
        metadata = dict(raw.get("metadata", {}))
        events = _normalize_events(
            raw_events=raw.get("events", []),
            run_spec=run_spec,
            condition=condition,
            output=output,
        )
        return AgentExecution(
            output=output,
            metrics=metrics,
            events=events,
            trace_refs=trace_refs,
            metadata=metadata,
        )

    output = {"text": str(raw)}
    events = _normalize_events(
        raw_events=[],
        run_spec=run_spec,
        condition=condition,
        output=output,
    )
    return AgentExecution(output=output, metrics={}, events=events, trace_refs=[], metadata={})


def _normalize_events(
    *,
    raw_events: Sequence[Any],
    run_spec: RunSpec,
    condition: Condition,
    output: Mapping[str, Any],
) -> list[Observation]:
    """Normalize external event payloads into unified observation records."""
    events: list[Observation] = []

    for index, raw_event in enumerate(raw_events):
        if not isinstance(raw_event, Mapping):
            continue
        events.append(
            Observation(
                timestamp=str(raw_event.get("timestamp", utc_now_iso())),
                record_id=str(
                    raw_event.get(
                        "record_id",
                        hash_identifier(
                            "evt",
                            {
                                "run_id": run_spec.run_id,
                                "index": index,
                                "event_type": raw_event.get("event_type", "event"),
                            },
                        ),
                    )
                ),
                text=str(raw_event.get("text", "")),
                session_id=str(raw_event.get("session_id", run_spec.run_id)),
                actor_id=str(raw_event.get("actor_id", "agent")),
                event_type=str(raw_event.get("event_type", "event")),
                meta_json=dict(raw_event.get("meta_json", {})),
                level=ObservationLevel(str(raw_event.get("level", ObservationLevel.STEP.value))),
                study_id=run_spec.study_id,
                run_id=run_spec.run_id,
                condition_id=condition.condition_id,
                trial_id=raw_event.get("trial_id"),
                step_id=raw_event.get("step_id"),
                tool_name=raw_event.get("tool_name"),
                evaluation_id=raw_event.get("evaluation_id"),
            )
        )

    if events:
        return events

    return [
        Observation(
            timestamp=utc_now_iso(),
            record_id=hash_identifier("evt", {"run_id": run_spec.run_id, "index": 0}),
            text=str(output.get("text", "")),
            session_id=run_spec.run_id,
            actor_id="agent",
            event_type="assistant_output",
            meta_json={"auto_generated": True},
            level=ObservationLevel.STEP,
            study_id=run_spec.study_id,
            run_id=run_spec.run_id,
            condition_id=condition.condition_id,
        )
    ]
