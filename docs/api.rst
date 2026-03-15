API
===

The ``design_research_experiments`` top-level package is the supported public
import surface for notebooks, scripts, and lightweight integrations. Everything
documented here is re-exported from ``design_research_experiments.__all__`` and
is intended to be imported from the package root rather than from deeper module
paths.

This reference is organized by job to be done:

- use the core study model when you are defining a study from first principles
- use recipes and bundles when you want opinionated defaults for common study types
- use design and execution helpers once the methodological contract is stable
- use reporting and export helpers after run results exist

For conceptual background, start with :doc:`concepts`. For an end-to-end flow,
start with :doc:`quickstart` or :doc:`examples/core/basic_usage`.

.. currentmodule:: design_research_experiments

.. note::

   If you are new to the package, the usual custom workflow is:

   1. define a :class:`~design_research_experiments.Study` with
      :class:`~design_research_experiments.Factor`,
      :class:`~design_research_experiments.Hypothesis`,
      :class:`~design_research_experiments.OutcomeSpec`, and
      :class:`~design_research_experiments.AnalysisPlan`
   2. materialize a design with
      :func:`~design_research_experiments.build_design` or
      :func:`~design_research_experiments.materialize_conditions`
   3. execute with :func:`~design_research_experiments.run_study`
   4. export analysis tables and reports with
      :func:`~design_research_experiments.export_analysis_tables` and the
      reporting helpers

Core Study Model
----------------

This section covers the typed objects that define what a study is, what varies,
what gets executed, and what execution returns.

- :doc:`reference/api/core_study_model`

Recipes and Bundles
-------------------

This section covers prebuilt study constructors, their typed override objects,
and the default benchmark bundles they assemble around common research tasks.

- :doc:`reference/api/recipes_and_bundles`

Design and Execution
--------------------

This section covers the public helpers that materialize conditions, generate DOE
tables, validate study definitions, and orchestrate run execution.

- :doc:`reference/api/design_and_execution`

Reporting and Exports
---------------------

This section covers canonical table exports and the lightweight reporting
helpers intended for manuscript drafting, summaries, and artifact packaging.

- :doc:`reference/api/reporting_and_exports`

.. toctree::
   :maxdepth: 2
   :hidden:

   reference/api/core_study_model
   reference/api/recipes_and_bundles
   reference/api/design_and_execution
   reference/api/reporting_and_exports
