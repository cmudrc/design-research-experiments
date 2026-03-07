design-research-experiments
===========================

The study-design and orchestration layer for reproducible design research.

What This Library Does
----------------------

``design-research-experiments`` defines study structure: hypotheses, factors,
blocking, admissible conditions, replications, and artifact flows. It
coordinates how agents, problems, and downstream analysis are connected in a
controlled experimental pipeline.

Highlights
----------

- Hypothesis schemas
- DOE builders
- Condition generation
- Run orchestration
- Replication control
- Artifact export

This library is the methodological control layer of the ecosystem. It is not
just another execution utility. It encodes experimental method in software and
is where design choices about rigor, admissibility, and reproducibility are made.

Typical Workflow
----------------

1. Define hypotheses, factors, outcomes, and constraints.
2. Materialize admissible conditions from the chosen DOE strategy.
3. Bind agent and problem references.
4. Execute runs and replications under explicit seed policy and budgets.
5. Export canonical artifacts for analysis and reporting.

Integration With The Ecosystem
------------------------------

The Design Research Collective maintains a modular ecosystem of libraries for
studying human and AI design behavior.

- **design-research-agents** implements AI participants, workflows, and tool-using reasoning patterns.
- **design-research-problems** provides benchmark design tasks, prompts, grammars, and evaluators.
- **design-research-analysis** analyzes the traces, event tables, and outcomes generated during studies.
- **design-research-experiments** sits above the stack as the study-design and orchestration layer, defining hypotheses, factors, conditions, replications, and artifact flows across agents, problems, and analysis.

Together these libraries support end-to-end design research pipelines, from
study design through execution and interpretation.

.. image:: _static/ecosystem-platform.svg
   :alt: Ecosystem diagram showing experiments above agents, problems, and analysis.
   :width: 100%
   :align: center

Start Here
----------

- :doc:`quickstart`
- :doc:`installation`
- :doc:`concepts`
- :doc:`typical_workflow`
- :doc:`examples/index`
- :doc:`api`
- `CONTRIBUTING.md <https://github.com/cmudrc/design-research-experiments/blob/main/CONTRIBUTING.md>`_

.. toctree::
   :maxdepth: 2
   :caption: Documentation
   :hidden:

   quickstart
   installation
   concepts
   typical_workflow
   examples/index
   api

.. toctree::
   :maxdepth: 2
   :caption: Development
   :hidden:

   dependencies_and_extras

.. toctree::
   :maxdepth: 2
   :caption: Additional Guides
   :hidden:

   study_structure_example
   examples_and_recipes
   cli_reference
   reference/index
