design-research-experiments
===========================

The study-design and orchestration layer for reproducible design research.

``design-research-experiments`` defines study structure: hypotheses, factors,
blocking, admissible conditions, replications, and artifact flows. It
coordinates how agents, problems, and downstream analysis are connected in a
controlled experimental pipeline.

This library is the methodological control layer of the ecosystem. It is not
just another execution utility. It encodes experimental method in software and
is where design choices about rigor, admissibility, and reproducibility are
made.

.. raw:: html

   <div class="drc-badge-row">
     <a class="drc-badge-link" href="https://github.com/cmudrc/design-research-experiments/actions/workflows/ci.yml">
       <img alt="CI" src="https://github.com/cmudrc/design-research-experiments/actions/workflows/ci.yml/badge.svg">
     </a>
     <a class="drc-badge-link" href="https://github.com/cmudrc/design-research-experiments/actions/workflows/ci.yml">
       <img alt="Coverage" src="https://raw.githubusercontent.com/cmudrc/design-research-experiments/main/.github/badges/coverage.svg">
     </a>
     <a class="drc-badge-link" href="https://github.com/cmudrc/design-research-experiments/actions/workflows/examples.yml">
       <img alt="Examples Passing" src="https://raw.githubusercontent.com/cmudrc/design-research-experiments/main/.github/badges/examples-passing.svg">
     </a>
     <a class="drc-badge-link" href="https://github.com/cmudrc/design-research-experiments/actions/workflows/examples.yml">
       <img alt="Public API In Examples" src="https://raw.githubusercontent.com/cmudrc/design-research-experiments/main/.github/badges/examples-api-coverage.svg">
     </a>
     <a class="drc-badge-link" href="https://github.com/cmudrc/design-research-experiments/actions/workflows/docs-pages.yml">
       <img alt="Docs" src="https://github.com/cmudrc/design-research-experiments/actions/workflows/docs-pages.yml/badge.svg">
     </a>
   </div>

.. note::

   **Start with** :doc:`quickstart` to define a first study, materialize a
   concrete condition set, and get into a reproducible local loop before
   branching into examples, recipes, and reference material.

Guides
------

Learn the study-modeling concepts, setup flow, and orchestration patterns that
shape a stable experimental pipeline.

- :doc:`quickstart`
- :doc:`installation`
- :doc:`concepts`
- :doc:`typical_workflow`
- :doc:`study_structure_example`
- :doc:`examples_and_recipes`
- :doc:`artifact_contract`

Examples
--------

Browse runnable examples that show the public API in action across the major
study-definition and execution surfaces.

- :doc:`examples/index`
- :doc:`examples/core/basic_usage`

Reference
---------

Look up the stable import surface, CLI behavior, reference pages, and optional
development extras.

- :doc:`api`
- :doc:`cli_reference`
- :doc:`reference/index`
- :doc:`dependencies_and_extras`

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
   :hidden:

   quickstart
   installation
   concepts
   typical_workflow
   study_structure_example
   examples_and_recipes
   artifact_contract
   examples/index
   api
   cli_reference
   reference/index
   dependencies_and_extras
