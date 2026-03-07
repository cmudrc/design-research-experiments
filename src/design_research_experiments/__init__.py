"""Public API exports for design-research-experiments."""

from .adapters.analysis import export_analysis_tables
from .adapters.problems import ProblemPacket
from .bundles import (
    BenchmarkBundle,
    grammar_problem_bundle,
    human_vs_agent_bundle,
    ideation_bundle,
    optimization_bundle,
)
from .conditions import Condition, Constraint, Factor, FactorKind, Level, materialize_conditions
from .designs import build_design, generate_doe
from .hypotheses import AnalysisPlan, Hypothesis, OutcomeSpec
from .recipes import (
    AgentArchitectureComparisonConfig,
    DiversityAndExplorationConfig,
    GrammarScaffoldConfig,
    HumanVsAgentProcessConfig,
    OptimizationBenchmarkConfig,
    PromptFramingConfig,
    RecipeStudyConfig,
    build_agent_architecture_comparison_study,
    build_diversity_and_exploration_study,
    build_grammar_scaffold_study,
    build_human_vs_agent_process_study,
    build_optimization_benchmark_study,
    build_prompt_framing_study,
)
from .reporting import (
    render_codebook,
    render_markdown_summary,
    render_methods_scaffold,
    render_significance_brief,
    write_markdown_report,
)
from .runners import resume_study, run_study
from .schemas import RunBudget, SeedPolicy
from .study import Block, RunResult, RunSpec, Study, validate_study

__all__ = [
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
