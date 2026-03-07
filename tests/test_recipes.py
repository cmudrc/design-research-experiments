"""Tests for recipe factory defaults and override semantics."""

from __future__ import annotations

import pytest

from design_research_experiments.bundles import optimization_bundle
from design_research_experiments.conditions import Factor, FactorKind, Level
from design_research_experiments.hypotheses import AnalysisPlan, OutcomeSpec
from design_research_experiments.recipes import (
    PromptFramingConfig,
    build_agent_architecture_comparison_study,
    build_diversity_and_exploration_study,
    build_grammar_scaffold_study,
    build_human_vs_agent_process_study,
    build_optimization_benchmark_study,
    build_prompt_framing_study,
)
from design_research_experiments.study import RunBudget, validate_study


@pytest.mark.parametrize(
    "builder",
    (
        build_agent_architecture_comparison_study,
        build_prompt_framing_study,
        build_grammar_scaffold_study,
        build_human_vs_agent_process_study,
        build_diversity_and_exploration_study,
        build_optimization_benchmark_study,
    ),
)
def test_recipe_factories_build_valid_default_studies(builder: object) -> None:
    """Each recipe factory should emit a validation-clean default study."""
    study = builder()
    assert validate_study(study) == []


def test_optimization_benchmark_recipe_has_coherent_bindings() -> None:
    """Optimization recipe defaults should keep hypothesis and analysis linkage consistent."""
    study = build_optimization_benchmark_study()

    hypothesis = study.hypotheses[0]
    assert hypothesis.hypothesis_id == "h1"
    assert hypothesis.linked_analysis_plan_id == "ap1"
    assert hypothesis.dependent_vars == ("primary_outcome",)

    analysis_plan = study.analysis_plans[0]
    assert analysis_plan.analysis_plan_id == "ap1"
    assert analysis_plan.hypothesis_ids == ("h1",)
    assert "mixed_effects" in analysis_plan.tests


def test_recipe_override_sections_replace_wholesale() -> None:
    """Non-None config fields should replace complete recipe sections."""
    custom_factors = (
        Factor(
            name="prompt_frame",
            description="Framing style",
            kind=FactorKind.MANIPULATED,
            levels=(
                Level(name="neutral", value="neutral"),
                Level(name="analogy", value="analogy"),
            ),
        ),
        Factor(
            name="prompt_difficulty",
            description="Difficulty",
            kind=FactorKind.MANIPULATED,
            levels=(
                Level(name="low", value="low"),
                Level(name="high", value="high"),
            ),
        ),
    )
    custom_outcomes = (
        OutcomeSpec(
            name="primary_outcome",
            source_table="runs",
            column="primary_outcome",
            aggregation="median",
            primary=True,
        ),
        OutcomeSpec(
            name="latency_s",
            source_table="runs",
            column="latency_s",
            aggregation="p90",
        ),
    )
    custom_analysis_plan = (
        AnalysisPlan(
            analysis_plan_id="ap1",
            hypothesis_ids=("h1",),
            tests=("regression",),
            outcomes=("primary_outcome",),
            export_tables=("custom_summary",),
        ),
    )
    custom_budget = RunBudget(replicates=2, parallelism=1, max_runs=20)

    study = build_prompt_framing_study(
        PromptFramingConfig(
            factors=custom_factors,
            outcomes=custom_outcomes,
            analysis_plans=custom_analysis_plan,
            design_spec={"kind": "constrained_factorial", "randomize": True},
            run_budget=custom_budget,
        )
    )

    assert study.factors == custom_factors
    assert study.outcomes == custom_outcomes
    assert study.analysis_plans == custom_analysis_plan
    assert study.design_spec == {"kind": "constrained_factorial", "randomize": True}
    assert study.run_budget is custom_budget
    assert validate_study(study) == []


def test_bundle_defaults_apply_and_explicit_values_win() -> None:
    """Bundle defaults should apply first and explicit IDs should override bundle IDs."""
    bundle = optimization_bundle()

    bundle_only = build_prompt_framing_study(PromptFramingConfig(bundle=bundle))
    assert bundle_only.problem_ids == bundle.problem_ids
    assert bundle_only.agent_specs == bundle.agent_specs

    explicit = build_prompt_framing_study(
        PromptFramingConfig(
            bundle=bundle,
            problem_ids=("explicit-problem",),
            agent_specs=("explicit-agent",),
        )
    )
    assert explicit.problem_ids == ("explicit-problem",)
    assert explicit.agent_specs == ("explicit-agent",)


def test_invalid_recipe_override_surfaces_validation_errors() -> None:
    """Inconsistent override combos should be surfaced by study validation."""
    study = build_prompt_framing_study(PromptFramingConfig(primary_outcomes=("missing",)))
    errors = validate_study(study)

    assert any("Primary outcome 'missing'" in error for error in errors)
