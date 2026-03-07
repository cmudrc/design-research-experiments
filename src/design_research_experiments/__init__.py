"""Public API exports for design-research-experiments."""

from .adapters.analysis import export_analysis_tables
from .bundles import BenchmarkBundle
from .conditions import Condition, Constraint, Factor, Level, materialize_conditions
from .designs import build_design
from .hypotheses import AnalysisPlan, Hypothesis, OutcomeSpec
from .runners import resume_study, run_study
from .study import Block, RunResult, RunSpec, Study, validate_study

__all__ = [
    "AnalysisPlan",
    "BenchmarkBundle",
    "Block",
    "Condition",
    "Constraint",
    "Factor",
    "Hypothesis",
    "Level",
    "OutcomeSpec",
    "RunResult",
    "RunSpec",
    "Study",
    "build_design",
    "export_analysis_tables",
    "materialize_conditions",
    "resume_study",
    "run_study",
    "validate_study",
]
