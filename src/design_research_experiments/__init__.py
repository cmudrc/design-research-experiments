"""Public API exports for design-research-experiments."""

from importlib.metadata import PackageNotFoundError, version

from .adapters.analysis import export_analysis_tables
from .adapters.problems import ProblemPacket, resolve_problem
from .bundles import (
    BenchmarkBundle,
    grammar_problem_bundle,
    human_vs_agent_bundle,
    ideation_bundle,
    optimization_bundle,
)
from .conditions import Condition, Constraint, Factor, FactorKind, Level, materialize_conditions
from .designs import DesignKind, DesignSpec, build_design, generate_doe
from .hypotheses import AnalysisPlan, Hypothesis, OutcomeSpec
from .recipes import (
    AgentArchitectureComparisonConfig,
    BivariateComparisonConfig,
    ComparisonStudyConfig,
    DiversityAndExplorationConfig,
    GrammarScaffoldConfig,
    HumanVsAgentProcessConfig,
    OptimizationBenchmarkConfig,
    PromptFramingConfig,
    RecipeStudyConfig,
    StrategyComparisonConfig,
    UnivariateComparisonConfig,
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
from .reporting import (
    render_codebook,
    render_markdown_summary,
    render_methods_scaffold,
    render_significance_brief,
    write_markdown_report,
)
from .runners import ConditionRunner, RunOutput, agent_result, resume_study, run_study
from .schemas import RunBudget, SeedPolicy
from .study import Block, RunResult, RunSpec, Study, validate_study

try:
    __version__ = version("design-research-experiments")
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = [
    "AgentArchitectureComparisonConfig",
    "AnalysisPlan",
    "BenchmarkBundle",
    "BivariateComparisonConfig",
    "Block",
    "ComparisonStudyConfig",
    "Condition",
    "ConditionRunner",
    "Constraint",
    "DesignKind",
    "DesignSpec",
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
    "RunOutput",
    "RunResult",
    "RunSpec",
    "SeedPolicy",
    "StrategyComparisonConfig",
    "Study",
    "UnivariateComparisonConfig",
    "__version__",
    "agent_result",
    "build_agent_architecture_comparison_study",
    "build_bivariate_comparison_study",
    "build_design",
    "build_diversity_and_exploration_study",
    "build_grammar_scaffold_study",
    "build_human_vs_agent_process_study",
    "build_optimization_benchmark_study",
    "build_prompt_framing_study",
    "build_strategy_comparison_study",
    "build_univariate_comparison_study",
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
    "resolve_problem",
    "resume_study",
    "run_study",
    "validate_study",
    "write_markdown_report",
]
