Artifact Contract
=================

``design-research-experiments`` owns the canonical artifact contract that the
rest of the library family reads and validates.

Treat this page as the stable public handoff surface for study outputs. The
guarantees below describe what downstream tools may safely build on. Internal
checkpoint files, temporary caches, and other implementation details are not
part of the compatibility contract unless they are explicitly listed here.

Versioning
----------

The canonical artifact set is versioned explicitly:

- ``manifest.json`` is the version authority for the exported artifact set.
- ``study.yaml`` carries its own ``schema_version`` field so a serialized study
  stays self-describing even before any runs complete.
- CSV artifacts keep plain headers only. They inherit the artifact-set version
  from ``manifest.json`` rather than embedding synthetic version rows.

Schema changes are communicated through three public surfaces together:

- ``manifest.json`` schema-version changes in the exported artifact set.
- this page, which is the human-readable contract of record.
- downstream docs such as the
  `design-research-analysis experiments handoff <https://cmudrc.github.io/design-research-analysis/experiments_handoff.html>`_
  when the change affects consumers.

Compatibility guarantee:

- Within one schema version, the artifact filenames below remain stable.
- Required fields and columns listed below remain compatibility-guaranteed.
- Additive metadata is allowed when it does not invalidate existing consumers.
- Breaking removals, renames, or semantic shifts require a schema-version bump
  and contract-doc update.

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

Public File Guarantees
----------------------

.. list-table::
   :header-rows: 1

   * - Artifact
     - Purpose
     - Minimum compatibility-guaranteed fields or columns
     - Consumer note
   * - ``study.yaml``
     - Serialize the study definition before and after execution.
     - ``schema_version``, ``study_id``, title/description, factors, outcomes, run budget
     - This is the human-readable study contract, not the downstream event table.
   * - ``manifest.json``
     - Declare the artifact-set version and export provenance.
     - ``schema_version``, ``study_id``, generation timestamp, run counts, model ids, provenance
     - This is the version authority for the directory-level handoff.
   * - ``conditions.csv``
     - Record one row per materialized condition.
     - ``study_id``, ``condition_id``, ``admissible``, ``constraint_messages``, ``assignment_meta_json``
     - Use this when rejoining factor assignments and admissibility explanations.
   * - ``runs.csv``
     - Record one row per executed run and its summary metadata.
     - ``study_id``, ``condition_id``, ``run_id``, ``problem_id``, ``problem_family``, ``agent_id``, ``agent_kind``, ``pattern_name``, ``model_name``, ``seed``, ``replicate``, ``status``, ``start_time``, ``end_time``, ``latency_s``, ``input_tokens``, ``output_tokens``, ``cost_usd``, ``primary_outcome``, ``trace_path``, ``manifest_path``
     - This is the primary study-context join target for downstream analysis.
   * - ``events.csv``
     - Record normalized event-level observations emitted during runs.
     - ``timestamp``, ``record_id``, ``text``, ``session_id``, ``actor_id``, ``event_type``, ``meta_json``
     - This is the first-class downstream input for ``design-research-analysis`` validation and workflow execution.
   * - ``evaluations.csv``
     - Record evaluator outputs keyed to runs.
     - ``run_id``, ``evaluator_id``, ``metric_name``, ``metric_value``, ``metric_unit``, ``aggregation_level``, ``notes_json``
     - Rejoin this with ``runs.csv`` after event-level analysis when you need scored outcomes.
   * - ``hypotheses.json``
     - Preserve machine-readable hypothesis definitions that informed the study.
     - Serialized hypotheses attached to the study
     - This remains stable enough for downstream reporting and audit trails.
   * - ``analysis_plan.json``
     - Preserve machine-readable analysis-plan definitions.
     - Serialized analysis-plan definitions attached to the study
     - This keeps interpretation intent coupled to the exported run bundle.

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

Compatibility Boundary
----------------------

The compatibility guarantee applies to the canonical filenames and required
fields listed above. It does not guarantee stability for:

- intermediate caches or checkpoints used only during execution
- internal Python object layouts
- unpublished serialization details that are not exported as canonical files

If a downstream consumer needs a new stable field, the correct path is to add
it to this contract and version it through ``manifest.json`` rather than
depending on incidental internal state.
