Docs Automation Baseline
========================

This page documents the shared docs and CI baseline for
``design-research-experiments``.

The experiments repo follows the common module pattern used across the family:
docs surfaces are checked for consistency and example health is reported
explicitly. Release state is tracked in GitHub milestones and release branches
instead of generated README callouts.

Shared Module Baseline
----------------------

.. list-table::
   :header-rows: 1

   * - Concern
     - Local utility
     - Workflow owner
     - Baseline expectation
   * - Docs consistency
     - ``scripts/check_docs_consistency.py``
     - ``ci.yml``
     - README, docs landing pages, and generated example surfaces stay aligned.
   * - Docstring policy
     - ``scripts/check_google_docstrings.py``
     - ``ci.yml``
     - Public APIs, scripts, and examples stay on the shared docstring policy.
   * - Coverage badge
     - ``scripts/generate_coverage_badge.py``
     - ``ci.yml``
     - Coverage badge stays in sync with the enforced repo coverage floor.
   * - Example docs generation
     - ``scripts/generate_example_docs.py``
     - ``examples.yml``
     - Runnable examples and recipes remain represented in the docs.
   * - Example reporting
     - ``scripts/generate_examples_metrics.py`` and ``scripts/generate_examples_badges.py``
     - ``examples.yml``
     - Example pass/fail and public-API coverage badges use the shared family format.
   * - Example boundary checks
     - ``scripts/check_example_api_coverage.py``
     - ``examples.yml``
     - Examples continue to exercise the documented public import surface.

Workflow Responsibilities
-------------------------

- ``ci.yml`` owns lint, type, test, coverage, docs-consistency, and docstring checks.
- ``examples.yml`` owns example execution, generated example docs, and example-derived badge metrics.
- ``docs-pages.yml`` owns the published docs build.
- ``workflow.yml`` remains the aggregate maintainer workflow entry point.

Experiments-Specific Notes
--------------------------

This repo's extra documentation work stays content-driven rather than
automation-driven:

- :doc:`artifact_contract` documents the public file-level handoff surface.
- :doc:`study_structure_example` and :doc:`examples_and_recipes` stay curated
  because they explain method, not just API reachability.

That means ``design-research-experiments`` does not need a repo-specific docs
generator beyond the shared example-doc pipeline. Its differentiation lives in
the study contract pages themselves.

When To Update This Page
------------------------

Refresh this page whenever workflow ownership changes or when a new docs,
examples, or badge utility becomes part of the shared experiments maintainer
loop.
