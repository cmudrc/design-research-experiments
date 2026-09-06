Artifact Contract
=================

``design-research-experiments`` owns the canonical artifact contract consumed
and validated by downstream tools, especially ``design-research-analysis``.

Treat this page as the stable public handoff surface for study outputs. The
guarantees below describe what downstream tools may safely build on. Internal
checkpoint files, temporary caches, and other implementation details are not
part of the compatibility contract unless they are explicitly listed here.

Versioning
----------

The canonical artifact set is versioned explicitly:

- The current artifact schema version is ``0.2.0``. This is distinct from the
  Python package version.
- Durable per-run evidence has its own additive schema, initially ``0.1.0``.
  Adding this evidence does not change the canonical artifact schema.
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
- ``runs.csv``: one row per planned run returned by orchestration, including
  explicit skipped rows, with study, condition, agent, problem, seed, status,
  latency, token, cost, and outcome metadata.
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
     - ``study_id``, ``condition_id``, ``admissible``, ``constraint_messages``, ``assignment_meta_json``; one flat column per factor; ``block_<name>`` per block assignment
     - Factor columns carry the materialized assignments. ``assignment_meta_json`` carries condition metadata, not the factor values.
   * - ``runs.csv``
     - Record one row per returned run, including planned runs skipped by orchestration.
     - ``study_id``, ``condition_id``, ``run_id``, ``problem_id``, ``problem_family``, ``agent_id``, ``agent_kind``, ``pattern_name``, ``model_name``, ``seed``, ``replicate``, ``status``, ``start_time``, ``end_time``, ``latency_s``, ``input_tokens``, ``output_tokens``, ``cost_usd``, ``primary_outcome``, ``trace_path``, ``manifest_path``
     - This is the primary study-context join target for downstream analysis.
   * - ``events.csv``
     - Record normalized event-level observations emitted during runs.
     - ``timestamp``, ``record_id``, ``text``, ``session_id``, ``actor_id``, ``event_type``, ``meta_json``
     - This is the first-class downstream input for ``design-research-analysis`` validation and workflow execution. Artifact-first joins additionally need ``run_id`` or a ``session_id`` equal to the corresponding ``runs.csv`` ``run_id``.
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

Durable Run Evidence
--------------------

``run_study`` persists a separately versioned evidence directory for every
planned run:

.. code-block:: text

   artifacts/
     runs/
       <run-id>/
         run.json
         observations.jsonl
         attachments/

This is the source record used to explain what was configured, what was
observed, and how each planned run ended. It is written independently of the
``checkpoint`` option. ``checkpoint=False`` disables resumable checkpoints; it
does not disable evidence capture.

``run.json`` schema ``0.1.0`` guarantees these top-level fields:

- ``schema_version`` and ``record_type``
- ``study_id``, ``condition_id``, and ``run_id``
- ``status``, ``status_reason``, ``attempted``, and ``terminal``
- ``configured`` and ``observed``
- ``timing`` and ``error``
- ``files`` and ``integrity``

``configured`` preserves the resolved agent/problem references, replicate,
seed, and configuration metadata. ``observed`` contains only material produced
or learned during execution: outputs, metrics, evaluator rows, provenance,
trace and artifact references, and observation counts. Raw observations are
stored one JSON object per line in ``observations.jsonl`` so downstream paper
drafting does not need live ``RunResult`` objects.

Lifecycle semantics are explicit:

- ``pending``: planned but not yet started
- ``running``: execution reached the run boundary
- ``success``: execution completed successfully
- ``failed``: execution completed with an isolated failure
- ``skipped``: orchestration intentionally did not start the run, for example
  after fail-fast was triggered

``success``, ``failed``, and ``skipped`` are terminal. If a process exits
abnormally, a remaining ``pending`` or ``running`` record exposes the incomplete
state rather than silently omitting the run or fabricating a terminal outcome.

Evidence writes replace ``run.json`` and ``observations.jsonl`` atomically.
The record includes a SHA-256 digest for the observation stream and hashes for
referenced files when they resolve inside the study directory. Known credential
fields and common token forms are redacted recursively. Sensitive participant
data is still the caller's responsibility and is not made safe merely by being
stored in this layout.

Use the public ``load_run_evidence_records(output_dir)`` helper to load and
validate the records, observation digests, and available referenced-file hashes
in a fresh process. Direct calls to
``export_canonical_artifacts`` do not synthesize run evidence because they do
not execute or observe runs.

Optional Paper-Draft Support
----------------------------

Paper support is an optional, explicit derivative of the canonical study files,
durable run evidence, and component-owned contribution packets. It uses the
separately versioned paper-draft contract ``0.1.0`` and does not change canonical
artifact schema ``0.2.0``.

``run_study`` and ``collect_paper_support`` never create paper-draft files.
``export_paper_support`` retains its support-only contract. The separate,
explicit ``export_paper_draft`` action writes a review artifact beneath the
canonical study output without changing artifact schema ``0.2.0``:

.. code-block:: text

   paper-draft/
     main.tex
     paper_draft.md
     references.bib
     paper_draft_manifest.json
     README.md
     sections/
       introduction.tex
       background.tex
       methods.tex
       results.tex
       discussion.tex
     tables/
     figures/

The draft manifest uses its own ``paper_draft_version``, declares
``document_status`` as ``paper-draft``, records source artifact schema and run
accounting, and maps each block to contribution provenance and evidence
references. Existing non-empty draft directories are never replaced without
explicit overwrite permission.

Calling the earlier ``export_paper_support`` helper writes:

.. code-block:: text

   artifacts/paper-draft/
     paper_support.json
     paper_outline.md
     references.json
     references.bib

``paper_support.json`` is the authority for the aggregate. It includes
``draft_status``, study ID, run accounting, evidence-labeled contributions,
deduplicated references with provenance, and unresolved reporting gaps.
``paper_outline.md`` is visibly marked as draft support rather than a
manuscript. ``references.bib`` contains only curated BibTeX received from a
component or the user; the exporter never guesses a missing entry.

The output directory is protected from implicit overwrite. See
:doc:`paper_draft_support` for the component packet shape and evidence
semantics.

CSV Column Guarantees
---------------------

These required columns always appear in the canonical CSV headers.

``conditions.csv``
   ``study_id``, ``condition_id``, ``admissible``, ``constraint_messages``,
   ``assignment_meta_json``, followed by one column per factor assignment and
   ``block_<name>`` columns for block assignments

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

Event-to-run Join Precondition
------------------------------

The minimum event header contract above intentionally remains compatible with
schema ``0.2.0``. Directory-first analysis helpers must still be able to map
each event to a row in ``runs.csv``. They resolve that relationship from a
non-empty ``run_id`` when present, then fall back to ``session_id`` and require
that value to equal ``runs.csv.run_id``.

The built-in agent execution adapter populates ``run_id`` and defaults
``session_id`` to the run identifier. The exporter does not, however, guarantee
``run_id`` for arbitrary observations supplied directly by callers, and a
caller may provide a different session identifier. Producers of such
observations must therefore set ``run_id`` explicitly or preserve the fallback
relationship. A future artifact-schema revision can make ``run_id`` a required
event column; doing so under ``0.2.0`` would overstate the current exporter
contract.

Validation
----------

Canonical exports are validated immediately after they are written. Contract
drift raises a ``ValidationError`` with a file- and column-specific message so
ecosystem integrations fail loudly rather than silently emitting malformed
artifacts.

Downstream consumers should treat the output directory itself as the handoff
unit. ``design-research-analysis`` reads and validates exported files through
top-level helpers such as
``design_research_analysis.build_condition_metric_table_from_artifacts(...)``
and ``design_research_analysis.validate_experiment_events(...)``.

Compatibility Boundary
----------------------

The compatibility guarantee applies to the canonical filenames and required
fields listed above, plus the separately versioned run-evidence layout. It does
not guarantee stability for:

- intermediate caches or checkpoints used only for resume behavior
- internal Python object layouts
- unpublished serialization details that are not exported as canonical files

If a downstream consumer needs a new stable field, the correct path is to add
it to the appropriate versioned contract rather than depending on incidental
internal state.
