Reference
=========

Use this section when you need the exact public contract, command-line behavior,
or a quick map of where each part of the package is implemented.

.. container:: docs-callout

   .. container:: docs-callout-body

      **Use the API page for imports and the CLI page for commands.** The module
      map below is the fastest way to orient yourself when you need to connect a
      concept in the docs to a concrete package area.

.. container:: docs-grid docs-grid--two

   .. container:: docs-card

      .. container:: docs-card-body

         **Public API**

         The compatibility-guaranteed import surface maps directly to
         ``design_research_experiments.__all__``.

         - :doc:`../api`

   .. container:: docs-card

      .. container:: docs-card-body

         **CLI reference**

         Review subcommands for study validation, design materialization,
         execution, resume flow, and export tasks.

         - :doc:`../cli_reference`

Primary modules and responsibilities:

- ``design_research_experiments.study``: study/run schemas and validation.
- ``design_research_experiments.hypotheses``: hypothesis/outcome/analysis-plan models.
- ``design_research_experiments.designs``: DOE builders and design materialization.
- ``design_research_experiments.conditions``: factor/block/constraint condition generation.
- ``design_research_experiments.runners``: execution orchestration, resume, checkpoint flow.
- ``design_research_experiments.artifacts``: canonical exports, manifests, and bundling.
- ``design_research_experiments.recipes``: reusable function-based study templates.
- ``design_research_experiments.adapters``: integration glue for agents/problems/analysis.
- ``design_research_experiments.io``: YAML/JSON/CSV/SQLite persistence helpers.

.. toctree::
   :maxdepth: 1
   :hidden:

   ../api
   ../cli_reference
