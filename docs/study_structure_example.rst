Study Structure Example
=======================

This minimal example shows how to encode one hypothesis, one manipulated factor,
replication control, one agent binding, one problem binding, and one output
location.

YAML Example
------------

.. code-block:: yaml

   study_id: prompt-framing-minimal
   title: Prompt framing pilot
   description: Minimal study structure example.

   hypotheses:
     - hypothesis_id: h1
       statement: Structured framing prompts improve judged idea quality.
       direction: positive
       factor_bindings: [prompt_style]
       outcome_bindings: [quality_score]

   factors:
     - name: prompt_style
       kind: manipulated
       levels:
         - name: baseline
           value: baseline
         - name: scaffolded
           value: scaffolded

   outcomes:
     - name: quality_score
       kind: continuous
       description: Mean evaluator score per run.

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

   from design_research_experiments import Study, build_design, validate_study

   study = Study.from_dict(
       {
           "study_id": "prompt-framing-minimal",
           "title": "Prompt framing pilot",
           "description": "Minimal study structure example.",
           "hypotheses": [
               {
                   "hypothesis_id": "h1",
                   "statement": "Structured framing prompts improve judged idea quality.",
                   "direction": "positive",
                   "factor_bindings": ["prompt_style"],
                   "outcome_bindings": ["quality_score"],
               }
           ],
           "factors": [
               {
                   "name": "prompt_style",
                   "kind": "manipulated",
                   "levels": [
                       {"name": "baseline", "value": "baseline"},
                       {"name": "scaffolded", "value": "scaffolded"},
                   ],
               }
           ],
           "outcomes": [
               {
                   "name": "quality_score",
                   "kind": "continuous",
                   "description": "Mean evaluator score per run.",
               }
           ],
           "run_budget": {"replicates": 2},
           "agent_specs": ["DirectLLMCall"],
           "problem_ids": ["ideation_peanut_shelling_fu_cagan_kotovsky_2010"],
           "output_dir": "artifacts/prompt-framing-minimal",
       }
   )

   errors = validate_study(study)
   if errors:
       raise RuntimeError("\n".join(errors))

   conditions = build_design(study)
   print(study.study_id, len(conditions))

Why This Matters
----------------

The same study object controls admissibility, replication, and artifact output
contracts. That is the core reason this package is the orchestration "hat"
over agents, problems, and analysis.
