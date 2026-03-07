"""Benchmark bundle presets for common study setups."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BenchmarkBundle:
    """Named bundle of agent/problem defaults for a study recipe."""

    bundle_id: str
    name: str
    description: str
    problem_ids: tuple[str, ...]
    agent_specs: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


def ideation_bundle() -> BenchmarkBundle:
    """Return a default ideation-focused benchmark bundle."""
    return BenchmarkBundle(
        bundle_id="ideation",
        name="Ideation Bundle",
        description="Problem prompts and agent variants for ideation studies.",
        problem_ids=("ideation-brief-a", "ideation-brief-b", "ideation-brief-c"),
        agent_specs=("baseline-agent", "creative-agent", "structured-agent"),
        metadata={"domain": "ideation"},
    )


def optimization_bundle() -> BenchmarkBundle:
    """Return a default optimization-focused benchmark bundle."""
    return BenchmarkBundle(
        bundle_id="optimization",
        name="Optimization Bundle",
        description="Parameterized optimization families for generalization studies.",
        problem_ids=("optimization-small", "optimization-medium", "optimization-large"),
        agent_specs=("deterministic-baseline", "self-learning-agent"),
        metadata={"domain": "optimization"},
    )


def grammar_problem_bundle() -> BenchmarkBundle:
    """Return a default grammar-scaffold benchmark bundle."""
    return BenchmarkBundle(
        bundle_id="grammar",
        name="Grammar Bundle",
        description="Grammar-constrained and unconstrained design-generation tasks.",
        problem_ids=("grammar-unconstrained", "grammar-guided", "grammar-tool-guided"),
        agent_specs=("direct-llm", "workflow-agent"),
        metadata={"domain": "grammar"},
    )


def human_vs_agent_bundle() -> BenchmarkBundle:
    """Return a default human-vs-agent teaming benchmark bundle."""
    return BenchmarkBundle(
        bundle_id="human-vs-agent",
        name="Human vs Agent Bundle",
        description="Human-only, AI-assisted, and hybrid collaboration tasks.",
        problem_ids=("teaming-session-a", "teaming-session-b"),
        agent_specs=("human-only", "ai-assisted", "hybrid-team"),
        metadata={"domain": "teaming"},
    )
