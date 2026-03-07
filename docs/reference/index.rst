Reference
=========

This reference section complements the top-level API contract.

Public Surface
--------------

The compatibility-guaranteed import surface is documented in :doc:`../api` and
maps directly to ``design_research_experiments.__all__``.

Module Map
----------

For command-line usage, see :doc:`../cli_reference`.


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
