Concepts
========

What Is A Study?
----------------

A study is a typed specification of empirical intent: hypotheses, factors,
conditions, outcomes, and execution budget. It is the unit that ties method to
execution artifacts.

Hypotheses and Outcomes
-----------------------

Hypotheses define expected effects. Outcomes define what is measured. Analysis
plans bind hypotheses and outcomes so interpretation contracts are explicit
before execution.

Factors and Levels
------------------

Factors represent manipulated or observed variables. Levels define the concrete
values used to materialize run conditions.

Blocks and Replications
-----------------------

Blocking controls nuisance variation. Replications support stability estimation
and reduce sensitivity to one-off stochastic runs.

Admissible Conditions
---------------------

Constraints determine which factor combinations are valid. Condition generation
is therefore methodological filtering, not just combinatorics.

DOE Builders
------------

The package includes multiple design builders (for example full factorial, latin
hypercube, and fractional two-level forms). The right choice depends on the
question, budget, and expected interactions.

Artifacts and Manifests
-----------------------

Canonical exports (study definitions, run tables, event tables, evaluation rows,
and manifests) are designed to feed downstream analysis and reporting without
ad-hoc schema translation. See :doc:`artifact_contract` for the file-level
guarantees and versioning rules.

The public compatibility promise lives at the file-contract level. Internal
checkpoint or cache details are intentionally outside that boundary unless they
are promoted into :doc:`artifact_contract`.

The "Hat" Role
--------------

This library sits above agents, problems, and analysis because it defines the
logic connecting them. It is the place where methodological rigor enters the
software stack.
