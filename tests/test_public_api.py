"""Tests for the curated public API."""

from __future__ import annotations

import design_research_experiments as drexp


def test_public_exports_match_curated_api() -> None:
    """Keep the top-level exports explicit and stable."""
    assert drexp.__all__ == [
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
