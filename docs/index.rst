design-research-experiments
===========================

A hypothesis-first orchestration layer for design research studies.

Use it to:

- define reproducible studies with explicit hypotheses and analysis mappings,
- materialize admissible DOE conditions with constraints and blocking, and
- execute studies to canonical artifacts that flow directly into analysis.

Highlights
----------

- Typed schemas for study design, hypotheses, outcomes, and run metadata.
- DOE builders for full factorial, constrained factorial, randomized block,
  repeated measures, latin square, and custom design matrices.
- Reproducible runners with deterministic seeds, checkpointing, and resume.
- Canonical artifact contracts for study manifests, runs, events, and evaluations.
- Thin adapters aligned to public APIs in sibling agent/problem/analysis libraries.

Typical Workflow
----------------

1. Define a ``Study`` with factors, blocks, constraints, and hypotheses.
2. Materialize admissible conditions from the study design.
3. Execute runs across agent/problem combinations with replications.
4. Export canonical artifacts and hand off to downstream analysis.

Start Here
----------

- :doc:`quickstart` for a compact end-to-end path.
- :doc:`dependencies_and_extras` for install profiles and maintainer checks.
- :doc:`examples/index` for generated runnable-script documentation.
- :doc:`api` for the curated top-level public API.
- :doc:`reference/index` for reference orientation and module map.
- `CONTRIBUTING.md <https://github.com/cmudrc/design-research-experiments/blob/main/CONTRIBUTING.md>`_
  for contribution workflow and quality expectations.

.. toctree::
   :maxdepth: 2
   :caption: Guides
   :hidden:

   quickstart
   dependencies_and_extras
   examples/index

.. toctree::
   :maxdepth: 2
   :caption: Reference
   :hidden:

   api
   reference/index
