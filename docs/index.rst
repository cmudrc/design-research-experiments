design-research-experiments
===========================

The study-design and orchestration layer for reproducible design research.

``design-research-experiments`` defines study structure: hypotheses, factors,
blocking, admissible conditions, replications, and artifact flows. It
coordinates how agents, problems, and downstream analysis are connected in a
controlled experimental pipeline.

This library is the methodological control layer of the ecosystem. It is not
just another execution utility. It encodes experimental method in software and
is where design choices about rigor, admissibility, and reproducibility are made.

.. container:: docs-callout

   .. container:: docs-callout-body

      **Start with** :doc:`quickstart` to validate a first study, materialize a
      design, and get the package into a runnable local loop before you dive into
      the deeper methodology and reference material.

.. container:: docs-grid

   .. container:: docs-card

      .. container:: docs-card-body

         **Guides**

         Learn the study-design vocabulary, setup flow, and reproducible workflow
         patterns that shape a clean experiment.

         - :doc:`guides/index`
         - :doc:`quickstart`
         - :doc:`typical_workflow`

   .. container:: docs-card

      .. container:: docs-card-body

         **Examples**

         Browse runnable examples that show the API in action, from small study
         definitions to recipe-backed runs.

         - :doc:`examples/index`
         - :doc:`examples/core/basic_usage`
         - :doc:`examples/recipes/recipe_prompt_framing_run`

   .. container:: docs-card

      .. container:: docs-card-body

         **Reference**

         Look up the stable import surface, CLI behavior, and the package areas
         responsible for study structure, design materialization, and reporting.

         - :doc:`reference/index`
         - :doc:`api`
         - :doc:`cli_reference`

The Design Research Collective maintains a modular ecosystem for studying human
and AI design behavior. ``design-research-experiments`` sits above agents,
problems, and analysis as the layer that defines hypotheses, factors,
conditions, replications, and artifact flow.

.. image:: _static/ecosystem-platform.svg
   :alt: Ecosystem diagram showing experiments above agents, problems, and analysis.
   :width: 100%
   :align: center

For contribution workflow and maintainer expectations, see `CONTRIBUTING.md
<https://github.com/cmudrc/design-research-experiments/blob/main/CONTRIBUTING.md>`_.

.. toctree::
   :maxdepth: 2
   :hidden:

   guides/index
   examples/index
   reference/index
