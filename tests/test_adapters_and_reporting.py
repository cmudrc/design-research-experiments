"""Tests for adapters, bundles, recipes, and reporting helpers."""

from __future__ import annotations

import importlib
import types
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
from design_research_experiments.recipes import (
    AgentArchitectureComparisonRecipe,
    DiversityAndExplorationRecipe,
    GrammarScaffoldRecipe,
    HumanVsAgentProcessRecipe,
    PromptFramingRecipe,
)
from design_research_experiments.reporting import (
    render_codebook,
    render_markdown_summary,
    render_methods_scaffold,
    render_significance_brief,
    write_markdown_report,
)
from design_research_experiments.schemas import Observation, ObservationLevel, RunStatus
from design_research_experiments.study import RunResult, RunSpec, validate_study

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

    class BadEvaluator:
        """Problem-like object with non-callable evaluator field."""

        problem_id = "bad"
        family = "bad"
        brief = "bad"
        evaluate = 42

    with pytest.raises(ValueError):
        problem_adapter.resolve_problem(BadEvaluator())

    assert problem_adapter.evaluate_problem(normalized, {}) == []


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
        """Provide a fake analysis module with a validator hook."""
        if name == "design_research_analysis":
            module = types.SimpleNamespace()

            def validate_events(path: Path) -> None:
                called.append(str(path))

            module.validate_events = validate_events
            return module
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


def test_recipes_bundles_and_reporting(tmp_path: Path) -> None:
    """Recipe/bundle/reporting utilities should build coherent outputs."""
    recipes = (
        AgentArchitectureComparisonRecipe(),
        PromptFramingRecipe(),
        GrammarScaffoldRecipe(),
        HumanVsAgentProcessRecipe(),
        DiversityAndExplorationRecipe(),
    )
    bundles = (
        ideation_bundle(),
        optimization_bundle(),
        grammar_problem_bundle(),
        human_vs_agent_bundle(),
    )

    assert len(bundles) == 4
    assert all(bundle.problem_ids for bundle in bundles)

    built_studies = [recipe.build_study() for recipe in recipes]
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
