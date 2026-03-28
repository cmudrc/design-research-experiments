"""Reusable, typed recipe builders for common lab workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .bundles import BenchmarkBundle, ideation_bundle, optimization_bundle
from .conditions import Constraint, Factor, FactorKind, Level
from .hypotheses import AnalysisPlan, Hypothesis, HypothesisDirection, HypothesisKind, OutcomeSpec
from .study import Block, RunBudget, SeedPolicy, Study

_AGENT_FACTOR_NAMES = frozenset({"agent_id", "agent", "agent_spec"})
_PROBLEM_FACTOR_NAMES = frozenset({"problem_id", "problem"})


@dataclass(slots=True)
class RecipeStudyConfig:
    """Shared typed overrides for recipe study construction.

    Any field set to ``None`` keeps the recipe default. Any field set to a non-``None``
    value replaces that section of the study definition wholesale.
    """

    study_id: str | None = None
    title: str | None = None
    description: str | None = None
    authors: tuple[str, ...] | None = None
    rationale: str | None = None
    tags: tuple[str, ...] | None = None
    hypotheses: tuple[Hypothesis, ...] | None = None
    factors: tuple[Factor, ...] | None = None
    blocks: tuple[Block, ...] | None = None
    constraints: tuple[Constraint, ...] | None = None
    design_spec: dict[str, Any] | None = None
    outcomes: tuple[OutcomeSpec, ...] | None = None
    analysis_plans: tuple[AnalysisPlan, ...] | None = None
    run_budget: RunBudget | None = None
    seed_policy: SeedPolicy | None = None
    output_dir: Path | None = None
    provenance_metadata: dict[str, Any] | None = None
    notes: str | None = None
    problem_ids: tuple[str, ...] | None = None
    agent_specs: tuple[str, ...] | None = None
    primary_outcomes: tuple[str, ...] | None = None
    secondary_outcomes: tuple[str, ...] | None = None
    bundle: BenchmarkBundle | None = None


@dataclass(slots=True)
class AgentArchitectureComparisonConfig(RecipeStudyConfig):
    """Overrides for the agent architecture comparison recipe."""


@dataclass(slots=True)
class PromptFramingConfig(RecipeStudyConfig):
    """Overrides for the prompt framing recipe."""


@dataclass(slots=True)
class GrammarScaffoldConfig(RecipeStudyConfig):
    """Overrides for the grammar scaffold recipe."""


@dataclass(slots=True)
class HumanVsAgentProcessConfig(RecipeStudyConfig):
    """Overrides for the human-vs-agent process recipe."""


@dataclass(slots=True)
class DiversityAndExplorationConfig(RecipeStudyConfig):
    """Overrides for the diversity and exploration recipe."""


@dataclass(slots=True)
class OptimizationBenchmarkConfig(RecipeStudyConfig):
    """Overrides for the optimization benchmark recipe."""


@dataclass(slots=True)
class ComparisonStudyConfig(RecipeStudyConfig):
    """Overrides for comparison-study recipe scaffolds."""

    comparison_factor: Factor | None = None
    secondary_factor: Factor | None = None


@dataclass(slots=True)
class UnivariateComparisonConfig(ComparisonStudyConfig):
    """Overrides for the univariate comparison recipe."""


@dataclass(slots=True)
class BivariateComparisonConfig(ComparisonStudyConfig):
    """Overrides for the bivariate comparison recipe."""


@dataclass(slots=True)
class StrategyComparisonConfig(ComparisonStudyConfig):
    """Overrides for the packaged-problem strategy comparison recipe."""


def _default_outcomes() -> tuple[OutcomeSpec, ...]:
    """Return baseline outcomes used by recipe scaffolds."""
    return (
        OutcomeSpec(
            name="primary_outcome",
            source_table="runs",
            column="primary_outcome",
            aggregation="mean",
            primary=True,
            expected_type="float",
            description="Primary study objective metric.",
        ),
        OutcomeSpec(
            name="latency_s",
            source_table="runs",
            column="latency_s",
            aggregation="mean",
            primary=False,
            expected_type="float",
            description="Run latency in seconds.",
        ),
    )


def _default_analysis_plan(
    hypothesis_id: str,
    *,
    tests: tuple[str, ...] = ("difference_in_means", "regression"),
    plots: tuple[str, ...] = ("condition_means",),
    export_tables: tuple[str, ...] = ("summary_by_condition",),
    random_effects: tuple[str, ...] = (),
) -> AnalysisPlan:
    """Return a compact default analysis plan."""
    return AnalysisPlan(
        analysis_plan_id="ap1",
        hypothesis_ids=(hypothesis_id,),
        tests=tests,
        outcomes=("primary_outcome",),
        random_effects=random_effects,
        plots=plots,
        export_tables=export_tables,
        multiple_comparison_policy="holm",
    )


def _apply_recipe_config(study: Study, config: RecipeStudyConfig | None) -> Study:
    """Apply typed config overrides to a default recipe study."""
    if config is None:
        return study

    resolved_study_id = config.study_id if config.study_id is not None else study.study_id
    study_output_dir = (
        study.output_dir if study.output_dir is not None else Path("artifacts") / study.study_id
    )

    if config.output_dir is not None:
        resolved_output_dir = config.output_dir
    elif config.study_id is not None:
        resolved_output_dir = Path("artifacts") / resolved_study_id
    else:
        resolved_output_dir = study_output_dir

    bundle_problem_ids = (
        config.bundle.problem_ids if config.bundle is not None else study.problem_ids
    )
    bundle_agent_specs = (
        config.bundle.agent_specs if config.bundle is not None else study.agent_specs
    )

    return Study(
        study_id=resolved_study_id,
        title=config.title if config.title is not None else study.title,
        description=config.description if config.description is not None else study.description,
        authors=config.authors if config.authors is not None else study.authors,
        rationale=config.rationale if config.rationale is not None else study.rationale,
        tags=config.tags if config.tags is not None else study.tags,
        hypotheses=config.hypotheses if config.hypotheses is not None else study.hypotheses,
        factors=config.factors if config.factors is not None else study.factors,
        blocks=config.blocks if config.blocks is not None else study.blocks,
        constraints=config.constraints if config.constraints is not None else study.constraints,
        design_spec=dict(config.design_spec)
        if config.design_spec is not None
        else dict(study.design_spec),
        outcomes=config.outcomes if config.outcomes is not None else study.outcomes,
        analysis_plans=(
            config.analysis_plans if config.analysis_plans is not None else study.analysis_plans
        ),
        run_budget=config.run_budget if config.run_budget is not None else study.run_budget,
        seed_policy=config.seed_policy if config.seed_policy is not None else study.seed_policy,
        output_dir=resolved_output_dir,
        provenance_metadata=(
            dict(config.provenance_metadata)
            if config.provenance_metadata is not None
            else dict(study.provenance_metadata)
        ),
        notes=config.notes if config.notes is not None else study.notes,
        problem_ids=config.problem_ids if config.problem_ids is not None else bundle_problem_ids,
        agent_specs=config.agent_specs if config.agent_specs is not None else bundle_agent_specs,
        primary_outcomes=(
            config.primary_outcomes
            if config.primary_outcomes is not None
            else study.primary_outcomes
        ),
        secondary_outcomes=(
            config.secondary_outcomes
            if config.secondary_outcomes is not None
            else study.secondary_outcomes
        ),
    )


def _comparison_level(
    *,
    name: str,
    value: str,
    label: str | None = None,
    is_baseline: bool = False,
    role: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Level:
    """Build one comparison-aware level with baseline/treatment metadata."""
    resolved_metadata = dict(metadata or {})
    resolved_metadata.setdefault("role", role or ("baseline" if is_baseline else "treatment"))
    resolved_metadata.setdefault("is_baseline", is_baseline)
    return Level(name=name, value=value, label=label, metadata=resolved_metadata)


def _comparison_factor(
    *,
    name: str,
    description: str,
    levels: tuple[Level, ...],
) -> Factor:
    """Build one manipulated factor annotated as a comparison axis."""
    return Factor(
        name=name,
        description=description,
        kind=FactorKind.MANIPULATED,
        levels=levels,
        metadata={"comparison_axis": True},
    )


def _slug_level_name(value: str, *, index: int, seen: set[str]) -> str:
    """Normalize a stable level name and keep duplicates unique."""
    base = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or f"level_{index}"
    candidate = base
    suffix = 2
    while candidate in seen:
        candidate = f"{base}_{suffix}"
        suffix += 1
    seen.add(candidate)
    return candidate


def _strategy_factor_from_bundle(bundle: BenchmarkBundle) -> Factor:
    """Build a default agent-strategy comparison factor from one benchmark bundle."""
    baseline_index = 0
    for index, agent_spec in enumerate(bundle.agent_specs):
        lowered = agent_spec.lower()
        if "baseline" in lowered or "random" in lowered:
            baseline_index = index
            break

    seen: set[str] = set()
    levels = tuple(
        _comparison_level(
            name=_slug_level_name(agent_spec, index=index, seen=seen),
            value=agent_spec,
            label=agent_spec.replace("-", " ").replace("_", " ").title(),
            is_baseline=index == baseline_index,
        )
        for index, agent_spec in enumerate(bundle.agent_specs)
    )
    return _comparison_factor(
        name="agent_id",
        description="Agent strategy or runtime binding under comparison.",
        levels=levels,
    )


def _resolve_comparison_factors(
    *,
    config: ComparisonStudyConfig | None,
    default_factors: tuple[Factor, ...],
    max_factors: int | None = None,
) -> tuple[Factor, ...]:
    """Resolve comparison factors with explicit precedence rules."""
    if config is not None and config.factors is not None:
        return config.factors

    resolved = list(default_factors)
    if config is not None:
        if config.comparison_factor is not None:
            if resolved:
                resolved[0] = config.comparison_factor
            else:
                resolved.append(config.comparison_factor)
        if config.secondary_factor is not None:
            if len(resolved) >= 2:
                resolved[1] = config.secondary_factor
            elif len(resolved) == 1:
                resolved.append(config.secondary_factor)
            else:
                resolved.extend(
                    factor
                    for factor in (config.comparison_factor, config.secondary_factor)
                    if factor is not None
                )

    if max_factors is not None:
        return tuple(resolved[:max_factors])
    return tuple(resolved)


def _comparison_hypothesis(
    *,
    factor_names: tuple[str, ...],
    label: str,
    statement: str,
    kind: HypothesisKind = HypothesisKind.EFFECT,
) -> Hypothesis:
    """Build a default comparison hypothesis."""
    return Hypothesis(
        hypothesis_id="h1",
        label=label,
        statement=statement,
        kind=kind,
        independent_vars=factor_names,
        dependent_vars=("primary_outcome",),
        direction=HypothesisDirection.DIFFERENT,
        linked_analysis_plan_id="ap1",
    )


def _finalize_comparison_bindings(
    study: Study,
    *,
    config: ComparisonStudyConfig | None,
    selected_bundle: BenchmarkBundle,
    default_problem_ids: tuple[str, ...],
    default_agent_specs: tuple[str, ...],
) -> Study:
    """Normalize bundle bindings so factor-bound comparisons do not Cartesian-expand."""
    factor_names = {factor.name for factor in study.factors}
    problem_ids = study.problem_ids
    agent_specs = study.agent_specs

    if factor_names & _PROBLEM_FACTOR_NAMES:
        problem_ids = ()
    elif config is not None and config.problem_ids is None and config.bundle is not None:
        problem_ids = selected_bundle.problem_ids
    elif not problem_ids:
        problem_ids = default_problem_ids

    if factor_names & _AGENT_FACTOR_NAMES:
        agent_specs = ()
    elif not agent_specs or (
        config is not None and config.agent_specs is None and config.bundle is not None
    ):
        agent_specs = default_agent_specs

    if problem_ids == study.problem_ids and agent_specs == study.agent_specs:
        return study
    return replace(study, problem_ids=problem_ids, agent_specs=agent_specs)


def _build_comparison_study(
    *,
    config: ComparisonStudyConfig | None,
    study_id: str,
    title: str,
    description: str,
    rationale: str,
    tags: tuple[str, ...],
    default_bundle: BenchmarkBundle,
    default_factors: tuple[Factor, ...],
    default_problem_ids: tuple[str, ...] | None = None,
    default_agent_specs: tuple[str, ...] | None = None,
    hypothesis_label: str,
    hypothesis_statement: str,
    hypothesis_kind: HypothesisKind = HypothesisKind.EFFECT,
    analysis_plots: tuple[str, ...] = ("condition_means",),
    analysis_export_tables: tuple[str, ...] = ("summary_by_condition",),
) -> Study:
    """Assemble a comparison-study scaffold and apply typed overrides."""
    selected_bundle = (
        config.bundle if config is not None and config.bundle is not None else default_bundle
    )
    resolved_factors = _resolve_comparison_factors(
        config=config,
        default_factors=default_factors,
    )
    factor_names = tuple(factor.name for factor in resolved_factors)
    resolved_problem_ids = default_problem_ids or selected_bundle.problem_ids
    resolved_agent_specs: tuple[str, ...]
    if default_agent_specs is None:
        resolved_agent_specs = (
            (selected_bundle.agent_specs[0],) if selected_bundle.agent_specs else ("default-agent",)
        )
    else:
        resolved_agent_specs = default_agent_specs

    defaults = Study(
        study_id=study_id,
        title=title,
        description=description,
        authors=("Design Research Collective",),
        rationale=rationale,
        tags=tags,
        hypotheses=(
            _comparison_hypothesis(
                factor_names=factor_names,
                label=hypothesis_label,
                statement=hypothesis_statement,
                kind=hypothesis_kind,
            ),
        ),
        factors=resolved_factors,
        design_spec={"kind": "constrained_factorial", "randomize": True},
        outcomes=_default_outcomes(),
        analysis_plans=(
            _default_analysis_plan(
                "h1",
                plots=analysis_plots,
                export_tables=analysis_export_tables,
            ),
        ),
        run_budget=RunBudget(replicates=2, parallelism=1),
        seed_policy=SeedPolicy(base_seed=37),
        output_dir=Path("artifacts") / study_id,
        problem_ids=resolved_problem_ids,
        agent_specs=resolved_agent_specs,
        primary_outcomes=("primary_outcome",),
        secondary_outcomes=("latency_s",),
    )
    configured = _apply_recipe_config(defaults, config)
    return _finalize_comparison_bindings(
        configured,
        config=config,
        selected_bundle=selected_bundle,
        default_problem_ids=resolved_problem_ids,
        default_agent_specs=resolved_agent_specs,
    )


def build_univariate_comparison_study(
    config: UnivariateComparisonConfig | None = None,
) -> Study:
    """Build a one-factor comparison study scaffold over packaged problems."""
    bundle = ideation_bundle()
    return _build_comparison_study(
        config=config,
        study_id="univariate-comparison",
        title="Univariate Comparison Study",
        description="Compare one manipulated condition across a packaged problem bundle.",
        rationale="Provide a compact scaffold for one-axis benchmark comparisons.",
        tags=("comparison", "univariate"),
        default_bundle=bundle,
        default_factors=(
            _comparison_factor(
                name="comparison_arm",
                description="Primary comparison arm.",
                levels=(
                    _comparison_level(
                        name="baseline",
                        value="baseline",
                        label="Baseline",
                        is_baseline=True,
                    ),
                    _comparison_level(name="treatment", value="treatment", label="Treatment"),
                ),
            ),
        ),
        hypothesis_label="Univariate Comparison Effect",
        hypothesis_statement="The comparison arm changes the primary outcome.",
    )


def build_bivariate_comparison_study(
    config: BivariateComparisonConfig | None = None,
) -> Study:
    """Build a two-factor comparison study scaffold over packaged problems."""
    bundle = ideation_bundle()
    return _build_comparison_study(
        config=config,
        study_id="bivariate-comparison",
        title="Bivariate Comparison Study",
        description="Compare two manipulated axes across a packaged problem bundle.",
        rationale="Provide a reusable scaffold for pairwise comparison designs and interactions.",
        tags=("comparison", "bivariate"),
        default_bundle=bundle,
        default_factors=(
            _comparison_factor(
                name="comparison_arm",
                description="Primary comparison arm.",
                levels=(
                    _comparison_level(
                        name="baseline",
                        value="baseline",
                        label="Baseline",
                        is_baseline=True,
                    ),
                    _comparison_level(name="treatment", value="treatment", label="Treatment"),
                ),
            ),
            _comparison_factor(
                name="prompt_regime",
                description="Secondary comparison axis.",
                levels=(
                    _comparison_level(
                        name="standard",
                        value="standard",
                        label="Standard",
                        is_baseline=True,
                    ),
                    _comparison_level(name="structured", value="structured", label="Structured"),
                ),
            ),
        ),
        hypothesis_label="Bivariate Comparison Effect",
        hypothesis_statement="The comparison axes jointly change the primary outcome.",
        analysis_plots=("condition_means", "interaction_means"),
        analysis_export_tables=("summary_by_condition", "summary_by_interaction"),
    )


def build_strategy_comparison_study(
    config: StrategyComparisonConfig | None = None,
) -> Study:
    """Build a packaged-problem strategy comparison study scaffold."""
    bundle = (
        config.bundle if config is not None and config.bundle is not None else optimization_bundle()
    )
    default_factor = (
        config.comparison_factor
        if config is not None and config.comparison_factor is not None
        else _strategy_factor_from_bundle(bundle)
    )
    return _build_comparison_study(
        config=config,
        study_id="strategy-comparison",
        title="Strategy Comparison Study",
        description="Compare named agent strategies on packaged benchmark problems.",
        rationale="Centralize canonical strategy-comparison wiring for packaged benchmarks.",
        tags=("comparison", "strategy", "benchmark"),
        default_bundle=bundle,
        default_factors=(default_factor,),
        default_problem_ids=bundle.problem_ids,
        default_agent_specs=bundle.agent_specs,
        hypothesis_label="Strategy Comparison Effect",
        hypothesis_statement=(
            "Agent strategy changes the primary outcome on the packaged benchmark."
        ),
        hypothesis_kind=HypothesisKind.ROBUSTNESS,
    )


def build_agent_architecture_comparison_study(
    config: AgentArchitectureComparisonConfig | None = None,
) -> Study:
    """Build a study comparing agent architecture choices across prompt difficulty."""
    hypothesis = Hypothesis(
        hypothesis_id="h1",
        label="Architecture Effect",
        statement="Agent architecture changes primary outcome.",
        kind=HypothesisKind.EFFECT,
        independent_vars=("agent_architecture", "prompt_difficulty"),
        dependent_vars=("primary_outcome",),
        direction=HypothesisDirection.DIFFERENT,
        linked_analysis_plan_id="ap1",
    )
    defaults = Study(
        study_id="agent-architecture-comparison",
        title="Agent Architecture Comparison",
        description="Compare architecture variants across prompt difficulty manipulations.",
        authors=("Design Research Collective",),
        rationale="Benchmark architecture and workflow pattern differences.",
        tags=("ideation", "architecture"),
        hypotheses=(hypothesis,),
        factors=(
            Factor(
                name="agent_architecture",
                description="Agent architecture family.",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="direct", value="direct-llm"),
                    Level(name="multistep", value="multi-step"),
                    Level(name="reflective", value="reflective"),
                ),
            ),
            Factor(
                name="prompt_difficulty",
                description="Prompt complexity level.",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="easy", value="easy"),
                    Level(name="medium", value="medium"),
                    Level(name="hard", value="hard"),
                ),
            ),
        ),
        blocks=(Block(name="problem_family", levels=("ideation", "optimization")),),
        design_spec={"kind": "constrained_factorial", "randomize": True},
        outcomes=_default_outcomes(),
        analysis_plans=(_default_analysis_plan("h1"),),
        run_budget=RunBudget(replicates=2, parallelism=1),
        seed_policy=SeedPolicy(base_seed=7),
        output_dir=Path("artifacts") / "agent-architecture-comparison",
        problem_ids=("problem-a", "problem-b"),
        agent_specs=("direct-llm", "multi-step", "reflective"),
        primary_outcomes=("primary_outcome",),
        secondary_outcomes=("latency_s",),
    )
    return _apply_recipe_config(defaults, config)


def build_prompt_framing_study(config: PromptFramingConfig | None = None) -> Study:
    """Build an ideation study with framing and prompt manipulation."""
    hypothesis = Hypothesis(
        hypothesis_id="h1",
        label="Prompt Framing Effect",
        statement="Prompt framing changes novelty and diversity outcomes.",
        kind=HypothesisKind.EFFECT,
        independent_vars=("prompt_frame", "prompt_difficulty"),
        dependent_vars=("primary_outcome",),
        direction=HypothesisDirection.DIFFERENT,
        linked_analysis_plan_id="ap1",
    )
    defaults = Study(
        study_id="prompt-framing-study",
        title="Prompt Framing Study",
        description="Measure framing effects in ideation tasks.",
        authors=("Design Research Collective",),
        rationale="Quantify framing manipulations in creative generation.",
        tags=("ideation", "framing"),
        hypotheses=(hypothesis,),
        factors=(
            Factor(
                name="prompt_frame",
                description="Prompt framing style.",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="neutral", value="neutral"),
                    Level(name="challenge", value="challenge"),
                    Level(name="analogy", value="analogy"),
                ),
            ),
            Factor(
                name="prompt_difficulty",
                description="Prompt difficulty.",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="low", value="low"),
                    Level(name="high", value="high"),
                ),
            ),
        ),
        blocks=(Block(name="domain", levels=("mobility", "health")),),
        design_spec={"kind": "randomized_block", "randomize": True},
        outcomes=_default_outcomes(),
        analysis_plans=(_default_analysis_plan("h1"),),
        run_budget=RunBudget(replicates=3, parallelism=1),
        seed_policy=SeedPolicy(base_seed=11),
        output_dir=Path("artifacts") / "prompt-framing-study",
        problem_ids=("ideation-1", "ideation-2", "ideation-3"),
        agent_specs=("baseline-agent", "creative-agent"),
        primary_outcomes=("primary_outcome",),
        secondary_outcomes=("latency_s",),
    )
    return _apply_recipe_config(defaults, config)


def build_grammar_scaffold_study(config: GrammarScaffoldConfig | None = None) -> Study:
    """Build a study comparing unconstrained and grammar-guided generation."""
    hypothesis = Hypothesis(
        hypothesis_id="h1",
        label="Grammar Guidance Effect",
        statement="Grammar-guided generation improves primary outcome.",
        kind=HypothesisKind.EFFECT,
        independent_vars=("generation_mode",),
        dependent_vars=("primary_outcome",),
        direction=HypothesisDirection.GREATER,
        linked_analysis_plan_id="ap1",
    )
    defaults = Study(
        study_id="grammar-scaffold-study",
        title="Grammar Scaffold Study",
        description="Benchmark constrained vs unconstrained generation modes.",
        authors=("Design Research Collective",),
        rationale="Assess structural scaffolds for design-generation quality.",
        tags=("grammar", "constrained-generation"),
        hypotheses=(hypothesis,),
        factors=(
            Factor(
                name="generation_mode",
                description="Generation scaffold type.",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="free", value="unconstrained"),
                    Level(name="grammar", value="grammar-guided"),
                    Level(name="tool", value="tool-guided"),
                ),
            ),
        ),
        blocks=(Block(name="problem_family", levels=("grammar", "text")),),
        design_spec={"kind": "full_factorial", "randomize": True},
        outcomes=_default_outcomes(),
        analysis_plans=(_default_analysis_plan("h1"),),
        run_budget=RunBudget(replicates=2, parallelism=1),
        seed_policy=SeedPolicy(base_seed=19),
        output_dir=Path("artifacts") / "grammar-scaffold-study",
        problem_ids=("grammar-1", "grammar-2"),
        agent_specs=("direct-llm", "workflow-agent"),
        primary_outcomes=("primary_outcome",),
        secondary_outcomes=("latency_s",),
    )
    return _apply_recipe_config(defaults, config)


def build_human_vs_agent_process_study(config: HumanVsAgentProcessConfig | None = None) -> Study:
    """Build a study comparing human-only, AI-assisted, and hybrid teams."""
    hypothesis = Hypothesis(
        hypothesis_id="h1",
        label="Teaming Configuration Effect",
        statement="Hybrid teams alter process traces and outcomes.",
        kind=HypothesisKind.MODERATION,
        independent_vars=("team_mode",),
        dependent_vars=("primary_outcome",),
        direction=HypothesisDirection.DIFFERENT,
        linked_analysis_plan_id="ap1",
    )
    defaults = Study(
        study_id="human-vs-agent-process",
        title="Human vs Agent Process Study",
        description="Capture communication and action traces across teaming modes.",
        authors=("Design Research Collective",),
        rationale="Compare human-only, AI-assisted, and hybrid workflows.",
        tags=("teaming", "process-trace"),
        hypotheses=(hypothesis,),
        factors=(
            Factor(
                name="team_mode",
                description="Team configuration.",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="human", value="human-only"),
                    Level(name="assist", value="ai-assisted"),
                    Level(name="hybrid", value="hybrid"),
                ),
            ),
        ),
        blocks=(Block(name="cohort", levels=("novice", "expert")),),
        design_spec={"kind": "repeated_measures", "counterbalance": True},
        outcomes=_default_outcomes(),
        analysis_plans=(_default_analysis_plan("h1"),),
        run_budget=RunBudget(replicates=1, parallelism=1),
        seed_policy=SeedPolicy(base_seed=23),
        output_dir=Path("artifacts") / "human-vs-agent-process",
        problem_ids=("teaming-1", "teaming-2"),
        agent_specs=("human-only", "ai-assisted", "hybrid"),
        primary_outcomes=("primary_outcome",),
        secondary_outcomes=("latency_s",),
    )
    return _apply_recipe_config(defaults, config)


def build_diversity_and_exploration_study(
    config: DiversityAndExplorationConfig | None = None,
) -> Study:
    """Build a study evaluating diversity and exploration outcomes."""
    hypothesis = Hypothesis(
        hypothesis_id="h1",
        label="Exploration Strategy Robustness",
        statement="Exploration-heavy strategies increase diversity metrics.",
        kind=HypothesisKind.ROBUSTNESS,
        independent_vars=("search_strategy",),
        dependent_vars=("primary_outcome",),
        direction=HypothesisDirection.GREATER,
        linked_analysis_plan_id="ap1",
    )
    defaults = Study(
        study_id="diversity-exploration",
        title="Diversity and Exploration Study",
        description="Assess exploration strategies across benchmark families.",
        authors=("Design Research Collective",),
        rationale="Characterize diversity-quality tradeoffs.",
        tags=("optimization", "diversity"),
        hypotheses=(hypothesis,),
        factors=(
            Factor(
                name="search_strategy",
                description="Exploration strategy.",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="greedy", value="greedy"),
                    Level(name="epsilon", value="epsilon-greedy"),
                    Level(name="ucb", value="ucb"),
                ),
            ),
        ),
        blocks=(Block(name="problem_family", levels=("bench-a", "bench-b", "bench-c")),),
        design_spec={"kind": "randomized_block", "randomize": True},
        outcomes=_default_outcomes(),
        analysis_plans=(_default_analysis_plan("h1"),),
        run_budget=RunBudget(replicates=2, parallelism=1),
        seed_policy=SeedPolicy(base_seed=29),
        output_dir=Path("artifacts") / "diversity-exploration",
        problem_ids=("opt-a", "opt-b", "opt-c"),
        agent_specs=("deterministic", "self-learning"),
        primary_outcomes=("primary_outcome",),
        secondary_outcomes=("latency_s",),
    )
    return _apply_recipe_config(defaults, config)


def build_optimization_benchmark_study(
    config: OptimizationBenchmarkConfig | None = None,
) -> Study:
    """Build a benchmark study for optimization generalization and learning effects."""
    hypothesis = Hypothesis(
        hypothesis_id="h1",
        label="Learning Strategy Generalization",
        statement="Self-learning agents outperform deterministic baselines across families.",
        kind=HypothesisKind.ROBUSTNESS,
        independent_vars=("learning_strategy", "tuning_regime"),
        dependent_vars=("primary_outcome",),
        direction=HypothesisDirection.GREATER,
        linked_analysis_plan_id="ap1",
    )
    bundle = optimization_bundle()
    defaults = Study(
        study_id="optimization-benchmark",
        title="Optimization Benchmark Study",
        description=(
            "Compare self-learning and deterministic baselines across optimization "
            "families and tuning regimes."
        ),
        authors=("Design Research Collective",),
        rationale="Measure optimization quality, robustness, and cross-family generalization.",
        tags=("optimization", "benchmark", "generalization"),
        hypotheses=(hypothesis,),
        factors=(
            Factor(
                name="learning_strategy",
                description="Agent learning approach.",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="deterministic", value="deterministic-baseline"),
                    Level(name="self_learning", value="self-learning-agent"),
                ),
            ),
            Factor(
                name="tuning_regime",
                description="Hyperparameter tuning regime.",
                kind=FactorKind.MANIPULATED,
                levels=(
                    Level(name="conservative", value="conservative"),
                    Level(name="aggressive", value="aggressive"),
                ),
            ),
        ),
        blocks=(Block(name="problem_family", levels=("small", "medium", "large")),),
        design_spec={"kind": "randomized_block", "randomize": True},
        outcomes=_default_outcomes(),
        analysis_plans=(
            AnalysisPlan(
                analysis_plan_id="ap1",
                hypothesis_ids=("h1",),
                tests=("difference_in_means", "mixed_effects"),
                outcomes=("primary_outcome",),
                random_effects=("problem_family",),
                plots=("family_condition_means",),
                export_tables=("optimization_summary",),
                multiple_comparison_policy="holm",
            ),
        ),
        run_budget=RunBudget(replicates=2, parallelism=1),
        seed_policy=SeedPolicy(base_seed=31),
        output_dir=Path("artifacts") / "optimization-benchmark",
        problem_ids=bundle.problem_ids,
        agent_specs=bundle.agent_specs,
        primary_outcomes=("primary_outcome",),
        secondary_outcomes=("latency_s",),
    )
    return _apply_recipe_config(defaults, config)


__all__ = [
    "AgentArchitectureComparisonConfig",
    "BivariateComparisonConfig",
    "ComparisonStudyConfig",
    "DiversityAndExplorationConfig",
    "GrammarScaffoldConfig",
    "HumanVsAgentProcessConfig",
    "OptimizationBenchmarkConfig",
    "PromptFramingConfig",
    "RecipeStudyConfig",
    "StrategyComparisonConfig",
    "UnivariateComparisonConfig",
    "build_agent_architecture_comparison_study",
    "build_bivariate_comparison_study",
    "build_diversity_and_exploration_study",
    "build_grammar_scaffold_study",
    "build_human_vs_agent_process_study",
    "build_optimization_benchmark_study",
    "build_prompt_framing_study",
    "build_strategy_comparison_study",
    "build_univariate_comparison_study",
]
