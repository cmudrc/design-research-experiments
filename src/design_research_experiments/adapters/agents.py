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

type AgentBinding = Any | Callable[[Condition], Any]

_AGENT_EXECUTION_PARAMETER_NAMES = frozenset(
    {
        "problem_packet",
        "problem",
        "brief",
        "run_spec",
        "condition",
        "seed",
        "prompt",
        "input",
        "request_id",
        "dependencies",
    }
)


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
    agent_bindings: Mapping[str, AgentBinding] | None = None,
) -> Any:
    """Resolve an agent reference into an executable object."""
    if not isinstance(agent_spec_ref, str):
        return agent_spec_ref

    if agent_bindings and agent_spec_ref in agent_bindings:
        return _materialize_agent_binding(agent_bindings[agent_spec_ref], condition)

    maybe_agent = _resolve_from_design_research_agents(agent_spec_ref)
    if maybe_agent is not None:
        return maybe_agent

    raise ValidationError(
        "Unknown agent spec "
        f"'{agent_spec_ref}'. Register an agent binding or pass an executable object."
    )


def execute_agent(
    *,
    agent_spec_ref: Any,
    run_spec: RunSpec,
    condition: Condition,
    problem_packet: ProblemPacket,
    agent_bindings: Mapping[str, AgentBinding] | None = None,
) -> AgentExecution:
    """Execute one agent run and normalize outputs, events, and trace refs."""
    executable = resolve_agent(
        agent_spec_ref,
        condition=condition,
        agent_bindings=agent_bindings,
    )
    raw = _invoke_agent(
        executable=executable,
        run_spec=run_spec,
        condition=condition,
        problem_packet=problem_packet,
    )
    return _normalize_agent_execution(raw=raw, run_spec=run_spec, condition=condition)


def _materialize_agent_binding(binding: AgentBinding, condition: Condition) -> Any:
    """Resolve one binding into a concrete executable for the current condition."""
    if _is_condition_scoped_binding(binding):
        return binding(condition)
    return binding


def _is_condition_scoped_binding(binding: AgentBinding) -> bool:
    """Return whether one binding is a condition-to-executable builder."""
    if not callable(binding):
        return False
    if hasattr(binding, "run") and callable(binding.run):
        return False

    try:
        parameters = inspect.signature(binding).parameters
    except (TypeError, ValueError):
        return False

    if any(name in _AGENT_EXECUTION_PARAMETER_NAMES for name in parameters):
        return False

    if any(
        parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        for parameter in parameters.values()
    ):
        return False

    positional_parameters = [
        parameter
        for parameter in parameters.values()
        if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    return len(parameters) == 1 and len(positional_parameters) == 1


def _resolve_from_design_research_agents(agent_id: str) -> Any | None:
    """Attempt loading one public executable or zero-arg agent constructor."""
    try:
        module = importlib.import_module("design_research_agents")
        exported = getattr(module, agent_id, None)
    except Exception:
        return None

    if exported is None:
        return None

    if inspect.isclass(exported):
        try:
            return exported()
        except TypeError:
            return None
        except Exception:
            return None

    if hasattr(exported, "run") and callable(exported.run):
        return exported

    if callable(exported):
        return exported

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
    problem_object = _problem_object_from_packet(problem_packet)
    dependencies = _build_agent_dependencies(
        problem_packet=problem_packet,
        problem_object=problem_object,
        run_spec=run_spec,
        condition=condition,
    )
    prompt_input = _select_agent_prompt_input(problem_packet, problem_object=problem_object)

    if "problem_packet" in parameters:
        kwargs["problem_packet"] = problem_packet
    if "problem" in parameters:
        kwargs["problem"] = problem_object if problem_object is not None else problem_packet
    if "brief" in parameters:
        kwargs["brief"] = problem_packet.brief
    if "run_spec" in parameters:
        kwargs["run_spec"] = run_spec
    if "condition" in parameters:
        kwargs["condition"] = condition
    if "seed" in parameters:
        kwargs["seed"] = run_spec.seed
    if (
        "prompt" in parameters
        and parameters["prompt"].kind is not inspect.Parameter.POSITIONAL_ONLY
    ):
        kwargs["prompt"] = prompt_input
    if "input" in parameters and parameters["input"].kind is not inspect.Parameter.POSITIONAL_ONLY:
        kwargs["input"] = prompt_input
    if "request_id" in parameters:
        kwargs["request_id"] = run_spec.run_id
    if "dependencies" in parameters:
        kwargs["dependencies"] = dependencies

    if kwargs:
        return callable_obj(**kwargs)

    if "dependencies" in parameters or "request_id" in parameters:
        return callable_obj(prompt_input, request_id=run_spec.run_id, dependencies=dependencies)

    try:
        return callable_obj(problem_packet, run_spec.seed)
    except TypeError:
        try:
            return callable_obj(problem_packet)
        except TypeError as exc:
            raise ValidationError("Resolved agent object is not executable.") from exc


def _normalize_agent_execution(
    *,
    raw: Any,
    run_spec: RunSpec,
    condition: Condition,
) -> AgentExecution:
    """Normalize raw execution output to canonical adapter shape."""
    if _is_execution_result(raw):
        return _normalize_execution_result(raw=raw, run_spec=run_spec, condition=condition)

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


def _problem_object_from_packet(problem_packet: ProblemPacket) -> Any | None:
    """Return the native packaged problem object when present."""
    return problem_packet.payload.get("problem_object")


def _select_agent_prompt_input(problem_packet: ProblemPacket, *, problem_object: Any | None) -> Any:
    """Select the stable prompt payload passed into agent-style run methods."""
    if problem_object is not None:
        return problem_object
    return problem_packet.brief


def _build_agent_dependencies(
    *,
    problem_packet: ProblemPacket,
    problem_object: Any | None,
    run_spec: RunSpec,
    condition: Condition,
) -> dict[str, object]:
    """Build one dependency payload for design-research-agents-style runtimes."""
    dependencies: dict[str, object] = {
        "problem_packet": problem_packet,
        "run_spec": run_spec,
        "condition": condition,
        "seed": run_spec.seed,
    }
    if problem_object is not None:
        dependencies["problem"] = problem_object
    return dependencies


def _is_execution_result(raw: Any) -> bool:
    """Return whether one object looks like a design-research-agents `ExecutionResult`."""
    if raw is None or isinstance(raw, Mapping):
        return False
    return all(hasattr(raw, attribute) for attribute in ("success", "output", "metadata"))


def _normalize_execution_result(
    *,
    raw: Any,
    run_spec: RunSpec,
    condition: Condition,
) -> AgentExecution:
    """Normalize a design-research-agents `ExecutionResult` into experiment outputs."""
    output_mapping = _extract_output_mapping(getattr(raw, "output", {}))
    output = _extract_execution_output(output_mapping)
    raw_metadata = getattr(raw, "metadata", {})
    metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    model_response = getattr(raw, "model_response", None)
    metadata.update(_extract_model_metadata(model_response))

    metrics: dict[str, Any] = {}
    raw_metrics = output_mapping.get("metrics")
    if isinstance(raw_metrics, Mapping):
        metrics.update(raw_metrics)
    _merge_usage_metrics(metrics, model_response)

    trace_refs = _extract_trace_refs(metadata)
    raw_events = output_mapping.get("events", [])
    normalized_raw_events = (
        raw_events
        if isinstance(raw_events, Sequence) and not isinstance(raw_events, (str, bytes))
        else []
    )
    events = _normalize_events(
        raw_events=normalized_raw_events,
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


def _extract_output_mapping(raw_output: Any) -> dict[str, Any]:
    """Normalize the raw execution output envelope to a plain mapping."""
    if isinstance(raw_output, Mapping):
        return dict(raw_output)
    return {}


def _extract_execution_output(output_mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve the canonical run output payload from a workflow-first envelope."""
    final_output = output_mapping.get("final_output")
    if isinstance(final_output, Mapping):
        return dict(final_output)
    if isinstance(final_output, str):
        return {"text": final_output}
    if final_output is not None:
        return {"final_output": final_output}

    if "text" in output_mapping:
        return {"text": str(output_mapping["text"])}
    if "model_text" in output_mapping:
        return {"text": str(output_mapping["model_text"])}
    return dict(output_mapping)


def _merge_usage_metrics(metrics: dict[str, Any], model_response: Any) -> None:
    """Merge token-usage metadata from a model response into the metrics mapping."""
    usage = getattr(model_response, "usage", None)
    if isinstance(usage, Mapping):
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
    else:
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)

    if isinstance(prompt_tokens, int):
        metrics.setdefault("input_tokens", prompt_tokens)
    if isinstance(completion_tokens, int):
        metrics.setdefault("output_tokens", completion_tokens)
    if isinstance(total_tokens, int):
        metrics.setdefault("total_tokens", total_tokens)


def _extract_model_metadata(model_response: Any) -> dict[str, Any]:
    """Extract stable model metadata from an optional LLM response."""
    metadata: dict[str, Any] = {}
    model_name = getattr(model_response, "model", None)
    if isinstance(model_name, str) and model_name.strip():
        metadata["model_name"] = model_name
    model_provider = getattr(model_response, "provider", None)
    if isinstance(model_provider, str) and model_provider.strip():
        metadata["model_provider"] = model_provider
    return metadata


def _extract_trace_refs(metadata: Mapping[str, Any]) -> list[str]:
    """Extract canonical trace references from execution metadata."""
    trace_refs: list[str] = []
    trace_path = metadata.get("trace_path")
    if isinstance(trace_path, str) and trace_path.strip():
        trace_refs.append(trace_path)
    raw_trace_refs = metadata.get("trace_refs")
    if isinstance(raw_trace_refs, Sequence) and not isinstance(raw_trace_refs, (str, bytes)):
        for value in raw_trace_refs:
            if isinstance(value, str) and value.strip() and value not in trace_refs:
                trace_refs.append(value)
    return trace_refs


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
