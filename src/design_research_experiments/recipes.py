"""Opinionated study recipes for common lab workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .conditions import Factor, FactorKind, Level
from .hypotheses import AnalysisPlan, Hypothesis, HypothesisDirection, HypothesisKind, OutcomeSpec
from .study import Block, RunBudget, SeedPolicy, Study


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


def _default_analysis_plan(hypothesis_id: str) -> AnalysisPlan:
    """Return a compact default analysis plan."""
    return AnalysisPlan(
        analysis_plan_id="ap1",
        hypothesis_ids=(hypothesis_id,),
        tests=("difference_in_means", "regression"),
        outcomes=("primary_outcome",),
        plots=("condition_means",),
        export_tables=("summary_by_condition",),
        multiple_comparison_policy="holm",
    )


@dataclass(slots=True)
class AgentArchitectureComparisonRecipe:
    """Recipe: compare agent architecture choices across prompt difficulty."""

    study_id: str = "agent-architecture-comparison"

    def build_study(self) -> Study:
        """Build a study instance from the recipe defaults."""
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
        return Study(
            study_id=self.study_id,
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
            output_dir=Path("artifacts") / self.study_id,
            problem_ids=("problem-a", "problem-b"),
            agent_specs=("direct-llm", "multi-step", "reflective"),
            primary_outcomes=("primary_outcome",),
            secondary_outcomes=("latency_s",),
        )


@dataclass(slots=True)
class PromptFramingRecipe:
    """Recipe: ideation study with framing and prompt manipulation."""

    study_id: str = "prompt-framing-study"

    def build_study(self) -> Study:
        """Build a study instance from the recipe defaults."""
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
        return Study(
            study_id=self.study_id,
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
            output_dir=Path("artifacts") / self.study_id,
            problem_ids=("ideation-1", "ideation-2", "ideation-3"),
            agent_specs=("baseline-agent", "creative-agent"),
            primary_outcomes=("primary_outcome",),
            secondary_outcomes=("latency_s",),
        )


@dataclass(slots=True)
class GrammarScaffoldRecipe:
    """Recipe: compare unconstrained and grammar-guided generation."""

    study_id: str = "grammar-scaffold-study"

    def build_study(self) -> Study:
        """Build a study instance from the recipe defaults."""
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
        return Study(
            study_id=self.study_id,
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
            output_dir=Path("artifacts") / self.study_id,
            problem_ids=("grammar-1", "grammar-2"),
            agent_specs=("direct-llm", "workflow-agent"),
            primary_outcomes=("primary_outcome",),
            secondary_outcomes=("latency_s",),
        )


@dataclass(slots=True)
class HumanVsAgentProcessRecipe:
    """Recipe: compare human-only, AI-assisted, and hybrid teams."""

    study_id: str = "human-vs-agent-process"

    def build_study(self) -> Study:
        """Build a study instance from the recipe defaults."""
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
        return Study(
            study_id=self.study_id,
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
            output_dir=Path("artifacts") / self.study_id,
            problem_ids=("teaming-1", "teaming-2"),
            agent_specs=("human-only", "ai-assisted", "hybrid"),
            primary_outcomes=("primary_outcome",),
            secondary_outcomes=("latency_s",),
        )


@dataclass(slots=True)
class DiversityAndExplorationRecipe:
    """Recipe: evaluate diversity and exploration outcomes across modes."""

    study_id: str = "diversity-exploration"

    def build_study(self) -> Study:
        """Build a study instance from the recipe defaults."""
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
        return Study(
            study_id=self.study_id,
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
            output_dir=Path("artifacts") / self.study_id,
            problem_ids=("opt-a", "opt-b", "opt-c"),
            agent_specs=("deterministic", "self-learning"),
            primary_outcomes=("primary_outcome",),
            secondary_outcomes=("latency_s",),
        )
