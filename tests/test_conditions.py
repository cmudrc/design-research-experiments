"""Tests for factor/constraint condition materialization."""

from __future__ import annotations

from design_research_experiments.conditions import (
    Constraint,
    ConstraintSeverity,
    Factor,
    FactorKind,
    Level,
    materialize_conditions,
)
from design_research_experiments.study import Block


def test_materialize_conditions_enforces_constraints() -> None:
    """Invalid assignments should be flagged as inadmissible for error constraints."""
    factors = (
        Factor(
            name="agent_pattern",
            description="Pattern",
            kind=FactorKind.MANIPULATED,
            levels=(Level(name="direct", value="direct"), Level(name="tool", value="tool")),
        ),
        Factor(
            name="tool_access",
            description="Tool access",
            kind=FactorKind.MANIPULATED,
            levels=(Level(name="off", value=False), Level(name="on", value=True)),
        ),
    )
    constraints = (
        Constraint(
            constraint_id="c1",
            description="Tool pattern requires tool access.",
            expression="agent_pattern != 'tool' or tool_access == True",
            severity=ConstraintSeverity.ERROR,
        ),
    )

    conditions = materialize_conditions(factors=factors, constraints=constraints)

    admissible = [condition for condition in conditions if condition.admissible]
    inadmissible = [condition for condition in conditions if not condition.admissible]

    assert len(conditions) == 4
    assert len(admissible) == 3
    assert len(inadmissible) == 1
    assert "c1" in inadmissible[0].constraint_messages[0]


def test_materialize_conditions_includes_blocks() -> None:
    """Block assignments should be included in each materialized condition."""
    factors = (
        Factor(
            name="difficulty",
            description="Difficulty",
            kind=FactorKind.MANIPULATED,
            levels=(Level(name="low", value="low"),),
        ),
    )
    blocks = (Block(name="problem_family", levels=("ideation", "optimization")),)

    conditions = materialize_conditions(factors=factors, blocks=blocks)

    assert len(conditions) == 2
    families = {condition.block_assignments["problem_family"] for condition in conditions}
    assert families == {"ideation", "optimization"}
