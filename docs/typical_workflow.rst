Typical Workflow
================

1. Choose inputs
----------------

Define hypotheses, outcomes, factors, levels, and admissibility constraints.

2. Instantiate core objects
---------------------------

Build a ``Study`` specification, including a typed ``DesignSpec``, run budgets,
replication policy, and either agent/problem bindings or a standalone
``ConditionRunner``.

3. Execute or inspect
---------------------

Materialize conditions, execute runs, and monitor checkpointed progress. In
interactive terminals, run execution shows a ``tqdm`` progress bar by default.
Importing the package does not initialize notebook progress support; ``tqdm``
is loaded only when a visible progress bar is requested.

4. Capture artifacts
--------------------

Export canonical artifacts (study manifest, conditions, runs, events,
evaluations) for downstream analysis. Treat the output directory as the stable
handoff unit and use :doc:`artifact_contract` when another repo or external
tool is going to build against those files.

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
