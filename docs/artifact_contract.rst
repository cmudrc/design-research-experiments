Artifact Contract
=================

``design-research-experiments`` owns the canonical artifact contract that the
rest of the library family reads and validates.

Versioning
----------

The canonical artifact set is versioned explicitly:

- ``manifest.json`` is the version authority for the exported artifact set.
- ``study.yaml`` carries its own ``schema_version`` field so a serialized study
  stays self-describing even before any runs complete.
- CSV artifacts keep plain headers only. They inherit the artifact-set version
  from ``manifest.json`` rather than embedding synthetic version rows.

Canonical Files
---------------

Every canonical export writes these files into one study output directory:

- ``study.yaml``: serialized study definition with ``schema_version``,
  ``study_id``, title/description, factors, outcomes, run budget, and the rest
  of the study model.
- ``manifest.json``: artifact-set manifest with ``schema_version``,
  ``study_id``, generation timestamp, run counts, model ids, and provenance.
- ``conditions.csv``: one row per materialized condition.
- ``runs.csv``: one row per executed run with study, condition, agent, problem,
  seed, status, latency, token, cost, and outcome metadata.
- ``events.csv``: one row per normalized observation/event emitted during runs.
- ``evaluations.csv``: one row per evaluator metric.

Two additional machine-readable files travel with the canonical set:

- ``hypotheses.json``: serialized hypotheses attached to the study.
- ``analysis_plan.json``: serialized analysis-plan definitions.

CSV Column Guarantees
---------------------

These required columns always appear in the canonical CSV headers.

``conditions.csv``
   ``study_id``, ``condition_id``, ``admissible``, ``constraint_messages``,
   ``assignment_meta_json``

``runs.csv``
   ``study_id``, ``condition_id``, ``run_id``, ``problem_id``,
   ``problem_family``, ``agent_id``, ``agent_kind``, ``pattern_name``,
   ``model_name``, ``seed``, ``replicate``, ``status``, ``start_time``,
   ``end_time``, ``latency_s``, ``input_tokens``, ``output_tokens``,
   ``cost_usd``, ``primary_outcome``, ``trace_path``, ``manifest_path``

``events.csv``
   ``timestamp``, ``record_id``, ``text``, ``session_id``, ``actor_id``,
   ``event_type``, ``meta_json``

``evaluations.csv``
   ``run_id``, ``evaluator_id``, ``metric_name``, ``metric_value``,
   ``metric_unit``, ``aggregation_level``, ``notes_json``

Validation
----------

Canonical exports are validated immediately after they are written. Contract
drift raises a ``ValidationError`` with a file- and column-specific message so
ecosystem integrations fail loudly rather than silently emitting malformed
artifacts.

Downstream consumers should treat the output directory itself as the handoff
unit. ``design-research-analysis`` reads the exported files through
``design_research_analysis.integration.load_experiment_artifacts(...)`` and
validates ``events.csv`` through
``design_research_analysis.integration.validate_experiment_events(...)``.
