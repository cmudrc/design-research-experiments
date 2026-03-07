"""Tests for the curated public API."""

from __future__ import annotations

import design_research_experiments as drexp


def test_public_exports_match_curated_api() -> None:
    """Keep the top-level exports explicit and stable."""
    assert drexp.__all__ == [
        "AgentArchitectureComparisonConfig",
        "AnalysisPlan",
        "BenchmarkBundle",
        "Block",
        "Condition",
        "Constraint",
        "DiversityAndExplorationConfig",
        "Factor",
        "FactorKind",
        "GrammarScaffoldConfig",
        "HumanVsAgentProcessConfig",
        "Hypothesis",
        "Level",
        "OptimizationBenchmarkConfig",
        "OutcomeSpec",
        "ProblemPacket",
        "PromptFramingConfig",
        "RecipeStudyConfig",
        "RunBudget",
        "RunResult",
        "RunSpec",
        "SeedPolicy",
        "Study",
        "build_agent_architecture_comparison_study",
        "build_design",
        "build_diversity_and_exploration_study",
        "build_grammar_scaffold_study",
        "build_human_vs_agent_process_study",
        "build_optimization_benchmark_study",
        "build_prompt_framing_study",
        "export_analysis_tables",
        "generate_doe",
        "grammar_problem_bundle",
        "human_vs_agent_bundle",
        "ideation_bundle",
        "materialize_conditions",
        "optimization_bundle",
        "render_codebook",
        "render_markdown_summary",
        "render_methods_scaffold",
        "render_significance_brief",
        "resume_study",
        "run_study",
        "validate_study",
        "write_markdown_report",
    ]
