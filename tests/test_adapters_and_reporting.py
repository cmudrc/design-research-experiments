"""Tests for adapters, bundles, recipes, and reporting helpers."""

from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from design_research_experiments.adapters import agents as agent_adapter
from design_research_experiments.adapters import analysis as analysis_adapter
from design_research_experiments.adapters import problems as problem_adapter
from design_research_experiments.bundles import (
    grammar_problem_bundle,
    human_vs_agent_bundle,
    ideation_bundle,
    optimization_bundle,
)
from design_research_experiments.conditions import Condition
from design_research_experiments.designs import build_design
from design_research_experiments.io import csv_io
from design_research_experiments.recipes import (
    build_agent_architecture_comparison_study,
    build_bivariate_comparison_study,
    build_diversity_and_exploration_study,
    build_grammar_scaffold_study,
    build_human_vs_agent_process_study,
    build_optimization_benchmark_study,
    build_prompt_framing_study,
    build_strategy_comparison_study,
    build_univariate_comparison_study,
)
from design_research_experiments.reporting import (
    render_codebook,
    render_markdown_summary,
    render_methods_scaffold,
    render_significance_brief,
    write_markdown_report,
)
from design_research_experiments.schemas import Observation, ObservationLevel, RunStatus
from design_research_experiments.study import RunBudget, RunResult, RunSpec, Study, validate_study

from .helpers import make_study


class _FakeProblem:
    """Problem-like object for adapter integration tests."""

    def __init__(self, problem_id: str) -> None:
        self.problem_id = problem_id
        self.family = "fake-family"
        self.brief = f"Brief {problem_id}"

    def evaluate(self, run_output: dict[str, Any]) -> list[dict[str, Any]]:
        """Return synthetic evaluation rows."""
        return [
            {
                "metric_name": "score",
                "metric_value": len(str(run_output.get("text", ""))),
            }
        ]


@dataclass(frozen=True)
class _FakePackagedEvaluation:
    """Dataclass-style packaged evaluation used for normalization tests."""

    objective_value: float
    is_feasible: bool
    higher_is_better: bool = False


class _FakePackagedProblem:
    """Packaged-problem-like object exposing metadata and render_brief."""

    def __init__(self) -> None:
        self.metadata = types.SimpleNamespace(
            problem_id="packaged-problem",
            title="Packaged Problem",
            summary="Synthetic packaged benchmark.",
            kind=types.SimpleNamespace(value="optimization"),
            capabilities=("prompt-packet", "optional-evaluator"),
            study_suitability=("intervention-ready",),
            feature_flags=("intervention-ready", "optional-evaluator"),
            implementation="design_research_problems.problems:FakeProblem",
        )
        self.statement_markdown = "Minimize the objective while staying feasible."

    def render_brief(self) -> str:
        """Return the canonical packaged brief text."""
        return "# Packaged Problem\n\nMinimize the objective while staying feasible."

    def evaluate(self, candidate: list[float]) -> _FakePackagedEvaluation:
        """Evaluate the extracted native candidate payload."""
        return _FakePackagedEvaluation(objective_value=float(sum(candidate)), is_feasible=True)


class _FakeDecisionProblem:
    """Decision-style packaged problem used for seeded baseline fallback tests."""

    def __init__(self) -> None:
        self.metadata = types.SimpleNamespace(
            problem_id="decision-problem",
            title="Decision Problem",
            summary="Synthetic decision benchmark.",
            kind=types.SimpleNamespace(value="decision"),
        )
        self.option_factors = (
            types.SimpleNamespace(key="shape", levels=("round", "square")),
            types.SimpleNamespace(key="size", levels=(1, 2, 3)),
        )

    def render_brief(self) -> str:
        """Return a stable packaged-problem brief."""
        return "Choose one allowed value for each factor."

    def evaluate(self, candidate: dict[str, object]) -> dict[str, object]:
        """Return a simple objective for a selected candidate."""
        return {
            "objective_value": 1.0 if candidate.get("shape") == "round" else 0.0,
            "higher_is_better": True,
        }


@dataclass(frozen=True)
class _FakeUsage:
    """Usage payload for fake execution-result tests."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class _FakeModelResponse:
    """Model response payload for fake execution-result tests."""

    model: str | None = None
    provider: str | None = None
    usage: _FakeUsage | dict[str, int] | None = None


class _FakeExecutionResult:
    """Minimal stand-in for design-research-agents ExecutionResult."""

    def __init__(
        self,
        *,
        output: dict[str, Any],
        metadata: dict[str, Any],
        model_response: _FakeModelResponse | None = None,
    ) -> None:
        self.success = True
        self.output = output
        self.metadata = metadata
        self.model_response = model_response


class _CallableAgent:
    """Simple callable agent wrapper with .run method."""

    def run(
        self,
        *,
        problem_packet: problem_adapter.ProblemPacket,
        run_spec: RunSpec,
        condition: Condition,
    ) -> dict[str, Any]:
        """Produce synthetic run output and trace events."""
        del condition
        return {
            "output": {"text": f"{problem_packet.problem_id}:{run_spec.seed}"},
            "metrics": {"input_tokens": 2, "output_tokens": 3, "cost_usd": 0.01},
            "events": [
                {
                    "event_type": "assistant_output",
                    "text": "agent message",
                    "actor_id": "agent",
                    "level": ObservationLevel.STEP.value,
                }
            ],
            "trace_refs": ["trace.json"],
            "metadata": {"model_name": "fake-model"},
        }


def test_problem_adapter_resolution_and_sampling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Problem adapter should resolve refs, evaluate outputs, and sample families."""
    packet = problem_adapter.resolve_problem(
        {
            "problem_id": "p-map",
            "family": "mapped",
            "brief": "mapped brief",
            "evaluator": lambda output: {"metric_name": "score", "metric_value": 1},
        }
    )
    assert packet.problem_id == "p-map"
    assert problem_adapter.evaluate_problem(packet, {"text": "x"})[0]["metric_name"] == "score"

    registry_packet = problem_adapter.ProblemPacket("p-reg", "reg", "brief")
    resolved_registry = problem_adapter.resolve_problem(
        "p-reg", registry={"p-reg": registry_packet}
    )
    assert resolved_registry is registry_packet

    calls: list[str] = []

    def fake_import(name: str) -> Any:
        """Return a dynamic module for upstream problem resolution."""
        if name == "design_research_problems":
            module = types.SimpleNamespace()

            def get_problem(problem_id: str) -> _FakeProblem:
                calls.append(problem_id)
                return _FakeProblem(problem_id)

            module.get_problem = get_problem
            return module
        return importlib.import_module(name)

    monkeypatch.setattr(problem_adapter.importlib, "import_module", fake_import)

    resolved = problem_adapter.resolve_problem("p-upstream")
    assert resolved.family == "fake-family"
    assert calls == ["p-upstream"]

    sampled = problem_adapter.sample_problem_packets(
        ["p1", "p2", "p3", "p4"],
        sample_size=3,
        seed=3,
        balanced_by_family=True,
    )
    assert len(sampled) == 3


def test_problem_adapter_object_and_errors() -> None:
    """Problem adapter should normalize objects and reject invalid evaluators."""

    class WithPrompt:
        """Problem-like object using prompt fallback."""

        problem_id = "prompt-problem"
        prompt = "prompt text"
        family = "prompt-family"

    normalized = problem_adapter.resolve_problem(WithPrompt())
    assert normalized.brief == "prompt text"
    assert problem_adapter.evaluate_problem(normalized, {}) == []

    packaged_problem = _FakePackagedProblem()
    packaged_packet = problem_adapter.resolve_problem(packaged_problem)
    assert packaged_packet.problem_id == "packaged-problem"
    assert packaged_packet.family == "optimization"
    assert packaged_packet.brief.startswith("# Packaged Problem")
    assert packaged_packet.metadata["title"] == "Packaged Problem"
    assert packaged_packet.metadata["summary"] == "Synthetic packaged benchmark."
    assert packaged_packet.metadata["problem_kind"] == "optimization"
    assert packaged_packet.metadata["capabilities"] == (
        "prompt-packet",
        "optional-evaluator",
    )
    assert packaged_packet.metadata["study_suitability"] == ("intervention-ready",)

    packaged_rows = problem_adapter.evaluate_problem(packaged_packet, {"candidate": [0.25, 0.75]})
    assert packaged_rows[0]["metric_name"] == "objective_value"
    assert packaged_rows[0]["metric_value"] == 1.0
    assert packaged_rows[1]["metric_name"] == "is_feasible"
    assert packaged_rows[1]["metric_value"] is True

    @dataclass(frozen=True)
    class _EvaluationWithMappingProxy:
        score: float
        candidate: object

    class MappingProxyEvaluatorProblem:
        """Problem-like object whose evaluator dataclass includes a mappingproxy field."""

        problem_id = "mappingproxy-problem"
        family = "decision"
        brief = "brief"

        def evaluate(self, _candidate: object) -> _EvaluationWithMappingProxy:
            return _EvaluationWithMappingProxy(
                score=0.5,
                candidate=types.MappingProxyType({"x": 1}),
            )

    mappingproxy_packet = problem_adapter.resolve_problem(MappingProxyEvaluatorProblem())
    mappingproxy_rows = problem_adapter.evaluate_problem(
        mappingproxy_packet,
        {"candidate": {"x": 1}},
    )
    assert mappingproxy_rows == [
        {
            "evaluator_id": "problem_evaluator",
            "metric_name": "score",
            "metric_value": 0.5,
            "metric_unit": "unitless",
            "aggregation_level": "run",
            "notes_json": {},
        }
    ]

    class BadEvaluator:
        """Problem-like object with non-callable evaluator field."""

        problem_id = "bad"
        family = "bad"
        brief = "bad"
        evaluate = 42

    with pytest.raises(ValueError):
        problem_adapter.resolve_problem(BadEvaluator())


def test_agent_adapter_execution_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Agent adapter should resolve/execute agent references across public paths."""
    condition = Condition("cond-1", {"variant": "a"}, {})
    run_spec = RunSpec(
        run_id="run-1",
        study_id="study-1",
        condition_id="cond-1",
        problem_id="p1",
        replicate=1,
        seed=5,
        agent_spec_ref="agent-a",
        problem_spec_ref="p1",
    )
    problem_packet = problem_adapter.ProblemPacket("p1", "fam", "brief")

    execution = agent_adapter.execute_agent(
        agent_spec_ref="agent-a",
        run_spec=run_spec,
        condition=condition,
        problem_packet=problem_packet,
        factories={"agent-a": lambda _condition: _CallableAgent()},
    )
    assert execution.output["text"].startswith("p1:")
    assert execution.events[0].event_type == "assistant_output"

    passthrough = agent_adapter.resolve_agent(_CallableAgent(), condition=condition)
    assert isinstance(passthrough, _CallableAgent)

    mapping_execution = agent_adapter.execute_agent(
        agent_spec_ref=lambda _problem_packet, _seed: "raw-text",
        run_spec=run_spec,
        condition=condition,
        problem_packet=problem_packet,
    )
    assert mapping_execution.output["text"] == "raw-text"

    def fake_import(name: str) -> Any:
        """Provide a fake design_research_agents module."""
        if name == "design_research_agents":
            return types.SimpleNamespace(agent_from_module=lambda: _CallableAgent())
        return importlib.import_module(name)

    monkeypatch.setattr(agent_adapter.importlib, "import_module", fake_import)
    resolved = agent_adapter.resolve_agent("agent_from_module", condition=condition)
    assert isinstance(resolved, _CallableAgent)

    with pytest.raises(ValueError):
        agent_adapter.resolve_agent("unknown-agent", condition=condition)

    with pytest.raises(ValueError):
        agent_adapter.execute_agent(
            agent_spec_ref=object(),
            run_spec=run_spec,
            condition=condition,
            problem_packet=problem_packet,
        )


def test_agent_adapter_fallbacks_and_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    """Agent adapter should cover import, callable, and event normalization fallbacks."""
    condition = Condition("cond-2", {"variant": "b"}, {})
    run_spec = RunSpec(
        run_id="run-2",
        study_id="study-2",
        condition_id="cond-2",
        problem_id="p2",
        replicate=1,
        seed=7,
        agent_spec_ref="agent-b",
        problem_spec_ref="p2",
    )
    problem_packet = problem_adapter.ProblemPacket("p2", "fam", "brief text")

    def import_failure(name: str) -> Any:
        """Simulate a missing upstream agent package."""
        if name == "design_research_agents":
            raise ImportError("missing package")
        return importlib.import_module(name)

    monkeypatch.setattr(agent_adapter.importlib, "import_module", import_failure)
    with pytest.raises(ValueError):
        agent_adapter.resolve_agent("missing-agent", condition=condition)

    def import_constructor_fallback(name: str) -> Any:
        """Provide an upstream constructor that cannot be zero-arg initialized."""
        if name == "design_research_agents":
            module = types.SimpleNamespace()

            def needs_problem_context(required_context: str) -> _CallableAgent:
                del required_context
                return _CallableAgent()

            module.needs_problem_context = needs_problem_context
            return module
        return importlib.import_module(name)

    monkeypatch.setattr(agent_adapter.importlib, "import_module", import_constructor_fallback)
    resolved = agent_adapter.resolve_agent("needs_problem_context", condition=condition)
    assert callable(resolved)

    def problem_and_brief_agent(*, problem: Any, brief: str) -> dict[str, Any]:
        """Use fallback keyword mapping for problem packet and brief text."""
        return {"output": {"text": f"{problem.problem_id}:{brief}"}}

    execution = agent_adapter.execute_agent(
        agent_spec_ref=problem_and_brief_agent,
        run_spec=run_spec,
        condition=condition,
        problem_packet=problem_packet,
    )
    assert execution.output["text"] == "p2:brief text"

    def problem_only_agent(problem: Any) -> dict[str, Any]:
        """Use the one-argument positional fallback after the two-arg call fails."""
        return {"output": {"text": problem.problem_id}}

    fallback_execution = agent_adapter.execute_agent(
        agent_spec_ref=problem_only_agent,
        run_spec=run_spec,
        condition=condition,
        problem_packet=problem_packet,
    )
    assert fallback_execution.output["text"] == "p2"

    def top_level_text_agent(*, seed: int) -> dict[str, Any]:
        """Exercise top-level text normalization and non-mapping event skipping."""
        del seed
        return {"text": "top-level text", "events": ["ignore-me"]}

    normalized_execution = agent_adapter.execute_agent(
        agent_spec_ref=top_level_text_agent,
        run_spec=run_spec,
        condition=condition,
        problem_packet=problem_packet,
    )
    assert normalized_execution.output == {"text": "top-level text"}
    assert len(normalized_execution.events) == 1
    assert normalized_execution.events[0].text == "top-level text"

    native_problem = _FakeProblem("p2-native")
    native_problem_packet = problem_adapter.ProblemPacket(
        "p2-native",
        "optimization",
        "native brief",
        payload={"problem_object": native_problem},
    )

    class ExecutionResultAgent:
        """Agent that expects design-research-agents-style prompt/dependencies input."""

        def run(
            self,
            prompt: object,
            *,
            request_id: str | None = None,
            dependencies: dict[str, object] | None = None,
        ) -> _FakeExecutionResult:
            assert prompt is native_problem
            assert request_id == run_spec.run_id
            assert dependencies is not None
            assert dependencies["problem_packet"] is native_problem_packet
            assert dependencies["problem"] is native_problem
            assert dependencies["run_spec"] is run_spec
            assert dependencies["condition"] is condition
            assert dependencies["seed"] == run_spec.seed
            return _FakeExecutionResult(
                output={
                    "final_output": {"candidate": {"choice": "baseline"}},
                    "metrics": {"primary_outcome": 0.75},
                    "events": [
                        {
                            "event_type": "assistant_output",
                            "text": "native output",
                            "actor_id": "agent",
                        }
                    ],
                },
                metadata={
                    "request_id": request_id or "",
                    "trace_path": "traces/run-2.jsonl",
                    "trace_dir": "traces",
                },
                model_response=_FakeModelResponse(
                    model="baseline-model",
                    provider="test-provider",
                    usage=_FakeUsage(prompt_tokens=8, completion_tokens=5, total_tokens=13),
                ),
            )

    execution_result_execution = agent_adapter.execute_agent(
        agent_spec_ref=ExecutionResultAgent(),
        run_spec=run_spec,
        condition=condition,
        problem_packet=native_problem_packet,
    )
    assert execution_result_execution.output == {"candidate": {"choice": "baseline"}}
    assert execution_result_execution.metrics["primary_outcome"] == 0.75
    assert execution_result_execution.metrics["input_tokens"] == 8
    assert execution_result_execution.metrics["output_tokens"] == 5
    assert execution_result_execution.metadata["request_id"] == run_spec.run_id
    assert execution_result_execution.metadata["trace_dir"] == "traces"
    assert execution_result_execution.metadata["model_name"] == "baseline-model"
    assert execution_result_execution.metadata["model_provider"] == "test-provider"
    assert execution_result_execution.trace_refs == ["traces/run-2.jsonl"]
    assert execution_result_execution.events[0].text == "native output"


def test_seeded_random_baseline_factories_support_public_and_fallback_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Seeded baseline factories should use the public agent when available or fall back."""
    condition = Condition("cond-baseline", {"variant": "baseline"}, {})
    run_spec = RunSpec(
        run_id="run-baseline",
        study_id="study-baseline",
        condition_id="cond-baseline",
        problem_id="decision-problem",
        replicate=1,
        seed=13,
        agent_spec_ref="SeededRandomBaselineAgent",
        problem_spec_ref="decision-problem",
    )
    problem_packet = problem_adapter.resolve_problem(_FakeDecisionProblem())

    factories = agent_adapter.make_seeded_random_baseline_factories()
    monkeypatch.setattr(agent_adapter, "_resolve_from_design_research_agents", lambda _id: None)

    fallback_execution = agent_adapter.execute_agent(
        agent_spec_ref="SeededRandomBaselineAgent",
        run_spec=run_spec,
        condition=condition,
        problem_packet=problem_packet,
        factories=factories,
    )
    assert fallback_execution.output["candidate"]["shape"] in {"round", "square"}
    assert fallback_execution.output["candidate"]["size"] in {1, 2, 3}
    assert fallback_execution.events[0].event_type == "baseline_candidate_selected"
    assert fallback_execution.metadata["agent_kind"] == "seeded_random_baseline"

    public_agent = _CallableAgent()
    monkeypatch.setattr(
        agent_adapter,
        "_resolve_from_design_research_agents",
        lambda agent_id: public_agent if agent_id == "SeededRandomBaselineAgent" else None,
    )
    public_execution = agent_adapter.execute_agent(
        agent_spec_ref="SeededRandomBaselineAgent",
        run_spec=run_spec,
        condition=condition,
        problem_packet=problem_adapter.ProblemPacket("p-public", "fam", "brief"),
        factories=agent_adapter.make_seeded_random_baseline_factories(),
    )
    assert public_execution.output["text"].startswith("p-public:")


def test_analysis_adapter_validation_and_exports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Analysis adapter should validate required columns and optional hooks."""
    study = make_study(tmp_path=tmp_path, study_id="analysis-study")
    conditions = build_design(study)

    run_spec = RunSpec(
        run_id="run-1",
        study_id=study.study_id,
        condition_id=conditions[0].condition_id,
        problem_id="problem-1",
        replicate=1,
        seed=11,
        agent_spec_ref="agent-a",
        problem_spec_ref="problem-1",
        execution_metadata={"problem_family": "fam"},
    )
    run_result = RunResult(
        run_id="run-1",
        status=RunStatus.SUCCESS,
        outputs={"text": "ok"},
        metrics={"primary_outcome": 1.0},
        observations=[
            Observation(
                timestamp="2026-01-01T00:00:00+00:00",
                record_id="evt-1",
                text="ok",
                session_id="run-1",
                actor_id="agent",
                event_type="assistant_output",
                level=ObservationLevel.STEP,
                run_id="run-1",
                study_id=study.study_id,
                condition_id=conditions[0].condition_id,
            )
        ],
        run_spec=run_spec,
    )

    validated_paths = analysis_adapter.export_analysis_tables(
        study,
        conditions=conditions,
        run_results=[run_result],
        output_dir=tmp_path / "analysis-out",
    )
    assert (validated_paths["events.csv"]).exists()

    errors = analysis_adapter.validate_unified_event_columns(
        [{"timestamp": "x", "record_id": "a", "text": "", "session_id": "s"}]
    )
    assert errors

    called: list[str] = []

    def fake_import(name: str) -> Any:
        """Provide a fake analysis integration module with an artifact validator hook."""
        if name == "design_research_analysis.integration":
            module = types.SimpleNamespace()
            def validate_experiment_events(path: Path) -> Any:
                rows = csv_io.read_csv(path)
                called.append(rows[0]["record_id"])
                return types.SimpleNamespace(is_valid=True, errors=())
            module.validate_experiment_events = validate_experiment_events
            return module
        if name == "design_research_analysis":
            return types.SimpleNamespace()
        return importlib.import_module(name)

    monkeypatch.setattr(analysis_adapter.importlib, "import_module", fake_import)
    analysis_adapter.export_analysis_tables(
        study,
        conditions=conditions,
        run_results=[run_result],
        output_dir=tmp_path / "analysis-hook",
        validate_with_analysis_package=True,
    )
    assert called


def test_analysis_adapter_raises_when_validation_report_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Analysis export should surface package validation failures when requested."""
    study = make_study(tmp_path=tmp_path, study_id="analysis-invalid")
    conditions = build_design(study)
    run_spec = RunSpec(
        run_id="run-invalid",
        study_id=study.study_id,
        condition_id=conditions[0].condition_id,
        problem_id="problem-1",
        replicate=1,
        seed=17,
        agent_spec_ref="agent-a",
        problem_spec_ref="problem-1",
    )
    run_result = RunResult(
        run_id="run-invalid",
        status=RunStatus.SUCCESS,
        outputs={"text": "ok"},
        observations=[
            Observation(
                timestamp="2026-01-01T00:00:00+00:00",
                record_id="evt-invalid",
                text="ok",
                session_id="run-invalid",
                actor_id="agent",
                event_type="assistant_output",
                level=ObservationLevel.STEP,
                run_id="run-invalid",
                study_id=study.study_id,
                condition_id=conditions[0].condition_id,
            )
        ],
        run_spec=run_spec,
    )

    def fake_import(name: str) -> Any:
        if name == "design_research_analysis.integration":
            module = types.SimpleNamespace()
            module.validate_experiment_events = lambda _path: types.SimpleNamespace(
                is_valid=False,
                errors=("missing required columns",),
            )
            return module
        if name == "design_research_analysis":
            return types.SimpleNamespace()
        return importlib.import_module(name)

    monkeypatch.setattr(analysis_adapter.importlib, "import_module", fake_import)
    with pytest.raises(ValueError, match="missing required columns"):
        analysis_adapter.export_analysis_tables(
            study,
            conditions=conditions,
            run_results=[run_result],
            output_dir=tmp_path / "analysis-invalid-hook",
            validate_with_analysis_package=True,
        )


def test_real_stack_interoperability_contracts(tmp_path: Path) -> None:
    """When sibling repos are available, the real stack should compose end to end."""
    problems_module = _import_sibling_module(
        "design_research_problems",
        repo_name="design-research-problems",
    )
    _import_sibling_module(
        "design_research_agents",
        repo_name="design-research-agents",
    )
    analysis_module = _import_sibling_module(
        "design_research_analysis",
        repo_name="design-research-analysis",
    )
    analysis_integration = _import_sibling_module(
        "design_research_analysis.integration",
        repo_name="design-research-analysis",
    )

    problem_id = "gmpb_default_dynamic_min"
    resolved_problem = problems_module.get_problem(problem_id)
    resolved_packet = problem_adapter.resolve_problem(resolved_problem)
    assert resolved_packet.problem_id == problem_id
    assert resolved_packet.family == resolved_problem.metadata.kind.value
    assert resolved_problem.metadata.title in resolved_packet.brief

    study = Study(
        study_id="real-stack-interop",
        title="Real stack interoperability",
        description="Verify packaged problems, agents, and analysis compose together.",
        output_dir=tmp_path / "real-stack-interop",
        problem_ids=(problem_id,),
        agent_specs=("SeededRandomBaselineAgent",),
        run_budget=RunBudget(replicates=1, parallelism=1, max_runs=1),
    )
    conditions = build_design(study)
    run_results = importlib.import_module("design_research_experiments.runners").run_study(
        study,
        conditions=conditions,
        show_progress=False,
    )

    assert len(run_results) == 1
    run_result = run_results[0]
    assert run_result.status == RunStatus.SUCCESS
    assert run_result.outputs
    assert run_result.metrics["primary_outcome"] is not None
    assert run_result.provenance_info["request_id"] == run_result.run_id

    exported = analysis_adapter.export_analysis_tables(
        study,
        conditions=conditions,
        run_results=run_results,
        output_dir=tmp_path / "real-stack-analysis",
        validate_with_analysis_package=True,
    )
    report = analysis_integration.validate_experiment_events(exported["events.csv"])
    loaded = analysis_integration.load_experiment_artifacts(exported["events.csv"])
    metric_rows = analysis_module.build_condition_metric_table(
        csv_io.read_csv(loaded["runs.csv"]),
        metric="primary_outcome",
        condition_column="agent_id",
        conditions=csv_io.read_csv(loaded["conditions.csv"]),
        evaluations=csv_io.read_csv(loaded["evaluations.csv"]),
    )
    assert report.is_valid
    assert metric_rows


def _import_sibling_module(module_name: str, *, repo_name: str) -> Any:
    """Import one sibling-repo module when the local workspace checkout is available."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        sibling_src = Path(__file__).resolve().parents[2] / repo_name / "src"
        if not sibling_src.exists():
            pytest.skip(f"{repo_name} checkout is not available in this workspace.")
        sibling_src_text = str(sibling_src)
        if sibling_src_text not in sys.path:
            sys.path.insert(0, sibling_src_text)
        try:
            return importlib.import_module(module_name)
        except ImportError as exc:
            pytest.skip(f"Unable to import {module_name}: {exc}")


def test_recipes_bundles_and_reporting(tmp_path: Path) -> None:
    """Recipe/bundle/reporting utilities should build coherent outputs."""
    recipe_builders = (
        build_agent_architecture_comparison_study,
        build_univariate_comparison_study,
        build_bivariate_comparison_study,
        build_strategy_comparison_study,
        build_prompt_framing_study,
        build_grammar_scaffold_study,
        build_human_vs_agent_process_study,
        build_diversity_and_exploration_study,
        build_optimization_benchmark_study,
    )
    bundles = (
        ideation_bundle(),
        optimization_bundle(),
        grammar_problem_bundle(),
        human_vs_agent_bundle(),
    )

    assert len(bundles) == 4
    assert all(bundle.problem_ids for bundle in bundles)

    built_studies = [builder() for builder in recipe_builders]
    for study in built_studies:
        study.output_dir = tmp_path / study.study_id
        assert validate_study(study) == []

    study = built_studies[0]
    conditions = build_design(study)

    run_result = RunResult(run_id="run-1", status=RunStatus.SUCCESS, run_spec=None)
    summary = render_markdown_summary(study, [run_result])
    methods = render_methods_scaffold(study)
    codebook = render_codebook(study, conditions[:1])
    brief = render_significance_brief(
        [{"test": "ttest", "outcome": "primary_outcome", "p_value": 0.04, "effect_size": 0.5}]
    )
    empty_brief = render_significance_brief([])

    report_text = "\n\n".join((summary, methods, codebook, brief, empty_brief))
    report_path = write_markdown_report(study.output_dir, "summary.md", report_text)

    assert "# Study Summary" in summary
    assert "## Methods" in methods
    assert "## Codebook" in codebook
    assert "No analysis rows provided" in empty_brief
    assert report_path.exists()
