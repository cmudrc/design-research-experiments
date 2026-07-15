Study Structure Example
=======================

This minimal example encodes one hypothesis, one manipulated factor, one
primary outcome, one analysis plan, replication control, runtime bindings, and
one output location. The YAML and Python forms represent the same public
schema.

YAML Example
------------

.. code-block:: yaml

   schema_version: 0.2.0
   study_id: prompt-framing-minimal
   title: Prompt framing pilot
   description: Minimal study structure example.

   hypotheses:
     - hypothesis_id: h1
       label: Prompt framing effect
       statement: Structured framing prompts improve judged idea quality.
       direction: different
       independent_vars: [prompt_style]
       dependent_vars: [quality_score]

   factors:
     - name: prompt_style
       description: Prompt framing style.
       kind: manipulated
       levels:
         - name: baseline
           value: baseline
         - name: scaffolded
           value: scaffolded

   outcomes:
     - name: quality_score
       source_table: runs
       column: primary_outcome
       aggregation: mean
       primary: true
       description: Mean evaluator score per run.

   analysis_plans:
     - analysis_plan_id: ap1
       hypothesis_ids: [h1]
       tests: [difference_in_means]
       outcomes: [quality_score]

   design_spec:
     kind: full_factorial

   run_budget:
     replicates: 2

   agent_specs:
     - DirectLLMCall

   problem_ids:
     - ideation_peanut_shelling_fu_cagan_kotovsky_2010

   output_dir: artifacts/prompt-framing-minimal

Python Example
--------------

.. code-block:: python

   from pathlib import Path

   import design_research_experiments as drex

   study = drex.Study(
       study_id="prompt-framing-minimal",
       title="Prompt framing pilot",
       description="Minimal study structure example.",
       hypotheses=(
           drex.Hypothesis(
               hypothesis_id="h1",
               label="Prompt framing effect",
               statement="Structured framing prompts improve judged idea quality.",
               independent_vars=("prompt_style",),
               dependent_vars=("quality_score",),
           ),
       ),
       factors=(
           drex.Factor(
               name="prompt_style",
               description="Prompt framing style.",
               kind=drex.FactorKind.MANIPULATED,
               levels=(
                   drex.Level(name="baseline", value="baseline"),
                   drex.Level(name="scaffolded", value="scaffolded"),
               ),
           ),
       ),
       outcomes=(
           drex.OutcomeSpec(
               name="quality_score",
               source_table="runs",
               column="primary_outcome",
               aggregation="mean",
               primary=True,
               description="Mean evaluator score per run.",
           ),
       ),
       analysis_plans=(
           drex.AnalysisPlan(
               analysis_plan_id="ap1",
               hypothesis_ids=("h1",),
               tests=("difference_in_means",),
               outcomes=("quality_score",),
           ),
       ),
       design_spec=drex.DesignSpec(kind=drex.DesignKind.FULL_FACTORIAL),
       run_budget=drex.RunBudget(replicates=2),
       agent_specs=("DirectLLMCall",),
       problem_ids=("ideation_peanut_shelling_fu_cagan_kotovsky_2010",),
       output_dir=Path("artifacts/prompt-framing-minimal"),
   )

   errors = drex.validate_study(study)
   if errors:
       raise RuntimeError("\n".join(errors))

   conditions = drex.build_design(study)
   print(study.study_id, len(conditions))

Why This Matters
----------------

The same study object controls admissibility, replication, and artifact output
contracts. That is the core reason this package is the orchestration "hat"
over agents, problems, and analysis.
