Docs Automation Baseline
========================

This page documents the shared docs and CI baseline for
``design-research-experiments``.

The experiments repo follows the common module pattern used across the family:
docs surfaces are checked for consistency and example health is reported
explicitly. Release state is tracked through package versions, GitHub Releases,
and focused PRs instead of generated README callouts or default monthly
milestones.

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
     - Internal navigation resolves, every top-level ``__all__`` export appears
       in the API inventory, and every checked-in example appears in its README.
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
     - ``ci.yml`` and ``docs-pages.yml``
     - Runnable examples and recipes remain represented in the docs.
   * - Example reporting
     - ``scripts/generate_examples_metrics.py`` and ``scripts/generate_examples_badges.py``
     - ``ci.yml``
     - Example pass/fail and public-API coverage badges use the shared family format.
   * - Example boundary checks
     - ``scripts/check_example_api_coverage.py``
     - ``examples.yml`` and ``ci.yml``
     - The runnable suite continues to reference the supported top-level import
       surface at the configured coverage threshold.

Workflow Responsibilities
-------------------------

- ``ci.yml`` owns lint, type, test, coverage, generated-doc consistency,
  docstring checks, example boundary checks, and example-derived badge metrics.
- ``examples.yml`` owns the standalone example-execution and public-API coverage checks.
- ``docs-pages.yml`` owns example-doc generation and the strict published docs build.
  Link checking remains the explicit ``make docs-linkcheck`` target.
- ``workflow.yml`` owns release builds and authorized PyPI publishing; it is not
  an aggregate validation workflow.

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
