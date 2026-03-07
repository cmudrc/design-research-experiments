"""Lightweight reporting helpers for study summaries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .conditions import Condition
from .study import RunResult, Study


def render_markdown_summary(study: Study, run_results: Sequence[RunResult]) -> str:
    """Render a compact markdown summary for one completed study."""
    status_counts: dict[str, int] = {}
    for run_result in run_results:
        key = run_result.status.value
        status_counts[key] = status_counts.get(key, 0) + 1

    lines = [
        f"# Study Summary: {study.title}",
        "",
        f"- Study ID: `{study.study_id}`",
        f"- Runs: `{len(run_results)}`",
        f"- Conditions: `{len(study.factors)}` factors, `{len(study.blocks)}` blocks",
        "- Primary outcomes: "
        f"{', '.join(study.primary_outcomes) if study.primary_outcomes else 'none'}",
        "",
        "## Status Counts",
    ]
    for status_name in sorted(status_counts):
        lines.append(f"- {status_name}: {status_counts[status_name]}")

    lines.extend(
        [
            "",
            "## Hypotheses",
        ]
    )
    if not study.hypotheses:
        lines.append("- none")
    else:
        for hypothesis in study.hypotheses:
            lines.append(f"- `{hypothesis.hypothesis_id}`: {hypothesis.statement}")

    return "\n".join(lines)


def render_significance_brief(analysis_rows: Sequence[Mapping[str, Any]]) -> str:
    """Render a short significance/effect-size brief from analysis outputs."""
    lines = ["## Significance Brief"]
    if not analysis_rows:
        lines.append("- No analysis rows provided.")
        return "\n".join(lines)

    for row in analysis_rows:
        test_name = row.get("test", "test")
        outcome = row.get("outcome", "outcome")
        p_value = row.get("p_value", "n/a")
        effect_size = row.get("effect_size", "n/a")
        lines.append(f"- {test_name} on `{outcome}`: p={p_value}, effect_size={effect_size}.")
    return "\n".join(lines)


def render_methods_scaffold(study: Study) -> str:
    """Render a methods-section scaffold for manuscript drafting."""
    lines = [
        "## Methods",
        "",
        f"Study ID: `{study.study_id}`",
        f"Design: `{study.design_spec.get('kind', 'unknown')}`",
        f"Replicates: `{study.run_budget.replicates}`",
        f"Seed policy: `{study.seed_policy.strategy}`",
        "",
        "### Factors",
    ]

    for factor in study.factors:
        lines.append(f"- `{factor.name}` ({factor.kind.value}): {factor.description}")

    lines.extend(["", "### Blocks"])
    for block in study.blocks:
        lines.append(f"- `{block.name}` with levels {list(block.levels)}")

    return "\n".join(lines)


def render_codebook(study: Study, conditions: Sequence[Condition]) -> str:
    """Render a simple codebook of factors, blocks, and condition IDs."""
    lines = ["## Codebook", "", "### Condition IDs"]
    for condition in conditions:
        factor_repr = condition.factor_assignments
        block_repr = condition.block_assignments
        lines.append(f"- `{condition.condition_id}` -> factors={factor_repr}, blocks={block_repr}")

    lines.extend(["", "### Outcomes"])
    for outcome in study.outcomes:
        source = f"{outcome.source_table}.{outcome.column}"
        lines.append(f"- `{outcome.name}` from `{source}` ({outcome.aggregation})")

    return "\n".join(lines)


def write_markdown_report(output_dir: str | Path, filename: str, content: str) -> Path:
    """Write markdown report content into the study artifacts directory."""
    path = Path(output_dir) / "artifacts" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
