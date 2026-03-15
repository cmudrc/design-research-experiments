Core Study Model
================

Use these types when you are describing a study from first principles rather
than starting from a prebuilt recipe. Together they define the research claim,
the admissible variation, the execution budget, and the normalized execution
records that flow through the rest of the package.

A typical custom flow is:

1. define hypotheses, outcomes, factors, and constraints
2. assemble a :class:`design_research_experiments.Study`
3. set execution controls such as :class:`design_research_experiments.RunBudget`
   and :class:`design_research_experiments.SeedPolicy`
4. materialize admissible conditions and run specifications
5. collect normalized run results for downstream analysis and reporting

.. currentmodule:: design_research_experiments

Research Structure
------------------

These objects capture the question being tested, the outcomes that matter, and
the analysis commitments attached to those outcomes.

.. autosummary::
   :nosignatures:

   Study
   Hypothesis
   OutcomeSpec
   AnalysisPlan

.. autoclass:: Study
   :members: from_dict, from_json, from_yaml, to_dict, to_json, to_yaml
   :member-order: bysource

.. autoclass:: Hypothesis

.. autoclass:: OutcomeSpec

.. autoclass:: AnalysisPlan

Variation and Admissibility
---------------------------

These objects describe what varies across conditions, which combinations are
allowed, and how those combinations are represented once materialized.

.. autosummary::
   :nosignatures:

   Factor
   FactorKind
   Level
   Block
   Constraint
   Condition

.. autoclass:: Factor
   :members: iter_values
   :member-order: bysource

.. autoclass:: FactorKind

.. autoclass:: Level

.. autoclass:: Block

.. autoclass:: Constraint
   :members: evaluate
   :member-order: bysource

.. autoclass:: Condition

Execution State
---------------

These objects describe how a study is turned into executable runs and how each
completed run is normalized for checkpointing, analysis, and export.

.. autosummary::
   :nosignatures:

   RunBudget
   SeedPolicy
   ProblemPacket
   RunSpec
   RunResult

.. autoclass:: RunBudget

.. autoclass:: SeedPolicy
   :members: derive_seed
   :member-order: bysource

.. autoclass:: ProblemPacket

.. autoclass:: RunSpec

.. autoclass:: RunResult
