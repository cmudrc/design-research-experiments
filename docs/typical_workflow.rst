Typical Workflow
================

1. Choose inputs
----------------

Define hypotheses, outcomes, factors, levels, and admissibility constraints.

2. Instantiate core objects
---------------------------

Build a ``Study`` specification, including run budgets, replication policy, and
agent/problem bindings.

3. Execute or inspect
---------------------

Materialize conditions, execute runs, and monitor checkpointed progress.

4. Capture artifacts
--------------------

Export canonical artifacts (study manifest, conditions, runs, events,
evaluations) for downstream analysis.

5. Connect to the next library
------------------------------

Use ``design-research-agents`` for participant behavior, use
``design-research-problems`` for task definitions, and analyze outputs with
``design-research-analysis``.

Why This Workflow Is Different
------------------------------

This workflow is about experimental control, not only batch execution. The
value is methodological: explicit admissibility, reproducible run construction,
and traceable artifact contracts across the ecosystem.
