"""Focused tests for hypothesis coercion, metrics helpers, and coverage guard branches."""

from __future__ import annotations

import pytest

from design_research_experiments.hypotheses import (
    AnalysisPlan,
    Contrast,
    Hypothesis,
    HypothesisDirection,
    HypothesisKind,
    Mediator,
    Moderator,
    OutcomeSpec,
    coerce_analysis_plan,
    coerce_hypothesis,
    coerce_outcome,
    validate_hypothesis_bindings,
)
from design_research_experiments.metrics import (
    compose_metrics,
    derive_process_metrics,
    evaluation_rows_from_mapping,
)
from design_research_experiments.schemas import Observation, ObservationLevel, ValidationError


def test_hypothesis_related_models_validate_required_fields() -> None:
    """Outcome, hypothesis, and analysis-plan models should reject empty required fields."""
    with pytest.raises(ValidationError, match=r"OutcomeSpec\.name"):
        OutcomeSpec(name="", source_table="runs", column="score", aggregation="mean")

    with pytest.raises(ValidationError, match=r"OutcomeSpec\.source_table"):
        OutcomeSpec(name="score", source_table="", column="score", aggregation="mean")

    with pytest.raises(ValidationError, match=r"OutcomeSpec\.column"):
        OutcomeSpec(name="score", source_table="runs", column="", aggregation="mean")

    with pytest.raises(ValidationError, match=r"Hypothesis\.hypothesis_id"):
        Hypothesis(hypothesis_id="", label="H1", statement="statement")

    with pytest.raises(ValidationError, match=r"Hypothesis\.label"):
        Hypothesis(hypothesis_id="h1", label="", statement="statement")

    with pytest.raises(ValidationError, match=r"Hypothesis\.statement"):
        Hypothesis(hypothesis_id="h1", label="H1", statement="")

    with pytest.raises(ValidationError, match=r"AnalysisPlan\.analysis_plan_id"):
        AnalysisPlan(analysis_plan_id="", hypothesis_ids=("h1",), tests=("ttest",))

    with pytest.raises(ValidationError, match="at least one hypothesis ID"):
        AnalysisPlan(analysis_plan_id="ap1", hypothesis_ids=(), tests=("ttest",))

    with pytest.raises(ValidationError, match="at least one test family"):
        AnalysisPlan(analysis_plan_id="ap1", hypothesis_ids=("h1",), tests=())


def test_hypothesis_coercion_and_binding_validation_cover_mapping_and_instance_paths() -> None:
    """Coercion helpers should preserve instances and normalize mapping payloads."""
    contrast = Contrast(label="existing", left="a", right="b")
    hypothesis = Hypothesis(
        hypothesis_id="h-existing",
        label="Existing",
        statement="existing statement",
        kind=HypothesisKind.EXPLORATORY,
        direction=HypothesisDirection.GREATER,
        contrast=contrast,
    )
    outcome = OutcomeSpec(
        name="score",
        source_table="runs",
        column="score",
        aggregation="mean",
    )
    analysis_plan = AnalysisPlan(
        analysis_plan_id="ap-existing",
        hypothesis_ids=("h-existing",),
        tests=("ttest",),
    )

    assert coerce_hypothesis(hypothesis) is hypothesis
    assert coerce_outcome(outcome) is outcome
    assert coerce_analysis_plan(analysis_plan) is analysis_plan

    coerced = coerce_hypothesis(
        {
            "hypothesis_id": "h1",
            "label": "H1",
            "statement": "Tools improve outcomes",
            "kind": "moderation",
            "independent_vars": ("tooling", "prompting"),
            "dependent_vars": ("score",),
            "moderators": ({"name": "experience", "levels": ("novice", "expert")},),
            "mediators": ({"name": "confidence", "description": "self report"},),
            "contrast": {"left": "tooling", "right": "baseline", "operation": "ratio"},
            "direction": "greater",
            "minimum_effect_of_interest": 0.2,
            "linked_analysis_plan_id": "ap1",
            "notes": "coverage regression",
        }
    )
    assert coerced.kind == HypothesisKind.MODERATION
    assert coerced.moderators[0].name == "experience"
    assert coerced.mediators[0].description == "self report"
    assert coerced.contrast is not None
    assert coerced.contrast.operation == "ratio"

    preserved_contrast = coerce_hypothesis(
        {
            "hypothesis_id": "h2",
            "label": "H2",
            "statement": "Existing instances stay intact",
            "moderators": (Moderator(name="role", levels=("designer",)),),
            "mediators": (Mediator(name="speed"),),
            "contrast": contrast,
        }
    )
    assert preserved_contrast.contrast is contrast
    assert preserved_contrast.moderators[0].name == "role"
    assert preserved_contrast.mediators[0].name == "speed"

    coerced_outcome = coerce_outcome(
        {
            "name": "latency",
            "source_table": "runs",
            "column": "latency_s",
            "aggregation": "mean",
            "primary": True,
            "expected_type": "float",
            "missing_data_policy": "drop",
            "description": "seconds",
        }
    )
    assert coerced_outcome.primary is True

    coerced_plan = coerce_analysis_plan(
        {
            "analysis_plan_id": "ap1",
            "hypothesis_ids": ("h1",),
            "tests": ("anova",),
            "outcomes": ("score",),
            "covariates": ("experience",),
            "random_effects": ("participant",),
            "filters": {"condition": "tool"},
            "multiple_comparison_policy": "holm",
            "plots": ("violin",),
            "export_tables": ("summary",),
            "notes": "ok",
        }
    )
    assert coerced_plan.filters == {"condition": "tool"}

    errors = validate_hypothesis_bindings(
        (
            Hypothesis(
                hypothesis_id="h-bad",
                label="Bad",
                statement="bad refs",
                independent_vars=("missing_factor",),
                dependent_vars=("missing_outcome",),
                linked_analysis_plan_id="missing-plan",
            ),
        ),
        factor_names=("tooling",),
        outcome_names=("score",),
        analysis_plan_ids=("ap1",),
    )
    assert len(errors) == 3
    assert any("missing_factor" in error for error in errors)
    assert any("missing_outcome" in error for error in errors)
    assert any("missing-plan" in error for error in errors)


def test_metric_helpers_derive_process_counts_and_safe_numeric_values() -> None:
    """Metric composition should merge process metrics and normalize numeric inputs."""
    observations = [
        Observation(
            timestamp="2026-01-01T00:00:00+00:00",
            record_id="obs-1",
            text="step",
            session_id="session",
            actor_id="agent",
            event_type="assistant_output",
            level=ObservationLevel.STEP,
        ),
        Observation(
            timestamp="2026-01-01T00:00:01+00:00",
            record_id="obs-2",
            text="tool",
            session_id="session",
            actor_id="tool",
            event_type="tool_call",
            level=ObservationLevel.TOOL_CALL,
        ),
        Observation(
            timestamp="2026-01-01T00:00:02+00:00",
            record_id="obs-3",
            text="meta",
            session_id="session",
            actor_id="agent",
            event_type="note",
            level=ObservationLevel.STEP,
        ),
    ]

    process = derive_process_metrics(observations)
    assert process == {
        "tool_call_count": 1,
        "step_event_count": 2,
        "unique_actor_count": 2,
    }

    metrics = compose_metrics(
        agent_metrics={"input_tokens": "bad", "output_tokens": None},
        evaluation_rows=[{"metric_name": "score", "metric_value": 0.75}],
        observations=observations,
        latency_s=1.25,
        cost_usd=0.5,
    )
    assert metrics["input_tokens"] == 0.0
    assert metrics["output_tokens"] == 0.0
    assert metrics["primary_outcome"] == 0.75
    assert metrics["tool_call_count"] == 1
    assert metrics["latency_s"] == 1.25
    assert metrics["cost_usd"] == 0.5

    preserved = compose_metrics(
        agent_metrics={"primary_outcome": 0.9, "input_tokens": 10, "output_tokens": 20},
        evaluation_rows=[{"metric_name": "score", "metric_value": 0.1}],
        observations=observations,
        latency_s=0.5,
        cost_usd=0.0,
    )
    assert preserved["primary_outcome"] == 0.9

    rows = evaluation_rows_from_mapping(
        run_id="run-1",
        evaluator_id="judge",
        metrics={"score": 0.9, "toxicity": 0.0},
        notes_json={"source": "unit-test"},
    )
    assert rows == [
        {
            "run_id": "run-1",
            "evaluator_id": "judge",
            "metric_name": "score",
            "metric_value": 0.9,
            "metric_unit": "unitless",
            "aggregation_level": "run",
            "notes_json": {"source": "unit-test"},
        },
        {
            "run_id": "run-1",
            "evaluator_id": "judge",
            "metric_name": "toxicity",
            "metric_value": 0.0,
            "metric_unit": "unitless",
            "aggregation_level": "run",
            "notes_json": {"source": "unit-test"},
        },
    ]
