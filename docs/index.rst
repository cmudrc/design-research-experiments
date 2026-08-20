design-research-experiments
===========================

The study-design and orchestration layer for reproducible design research.

What This Library Does
----------------------

``design-research-experiments`` defines study structure: hypotheses, factors,
blocking, admissible conditions, replications, and artifact flows. It
coordinates how agents, problems, and downstream analysis are connected in a
controlled experimental pipeline.

This library is the methodological control layer of the
CMU Design Research Collective design-research ecosystem. It is not just
another execution utility. It encodes experimental method in software and is where design
choices about rigor, admissibility, and reproducibility are made.

.. container:: drc-home-badges

   .. raw:: html

      <div class="drc-badge-row">
        <a class="drc-badge-link" href="https://github.com/cmudrc/design-research-experiments/actions/workflows/ci.yml">
          <img alt="CI" src="https://github.com/cmudrc/design-research-experiments/actions/workflows/ci.yml/badge.svg">
        </a>
        <a class="drc-badge-link" href="https://github.com/cmudrc/design-research-experiments/actions/workflows/ci.yml">
          <img alt="Coverage" src="https://raw.githubusercontent.com/cmudrc/design-research-experiments/HEAD/.github/badges/coverage.svg">
        </a>
        <a class="drc-badge-link" href="https://github.com/cmudrc/design-research-experiments/actions/workflows/examples.yml">
          <img alt="Examples Passing" src="https://raw.githubusercontent.com/cmudrc/design-research-experiments/HEAD/.github/badges/examples-passing.svg">
        </a>
        <a class="drc-badge-link" href="https://github.com/cmudrc/design-research-experiments/actions/workflows/examples.yml">
          <img alt="API in Examples" src="https://raw.githubusercontent.com/cmudrc/design-research-experiments/HEAD/.github/badges/examples-api-coverage.svg">
        </a>
        <a class="drc-badge-link" href="https://github.com/cmudrc/design-research-experiments/actions/workflows/docs-pages.yml">
          <img alt="Docs" src="https://github.com/cmudrc/design-research-experiments/actions/workflows/docs-pages.yml/badge.svg">
        </a>
        <a class="drc-badge-link" href="https://pypi.org/project/design-research-experiments/">
          <img alt="PyPI Version" src="https://img.shields.io/pypi/v/design-research-experiments.svg">
        </a>
        <a class="drc-badge-link" href="https://pypi.org/project/design-research-experiments/">
          <img alt="Python Versions" src="https://img.shields.io/pypi/pyversions/design-research-experiments.svg">
        </a>
      </div>

Quality Signals
---------------

- ``Coverage`` reports total line coverage for the default deterministic test
  suite; CI requires at least 95%.
- ``Examples Passing`` reports checked-in example scripts that execute
  successfully in the examples workflow.
- ``API in Examples`` reports curated top-level ``__all__`` exports referenced
  by runnable examples. ``N/N`` means every supported top-level export appears
  in at least one example, and CI requires 100%.

Run ``make coverage``, ``make examples-test``, and ``make examples-coverage``
to reproduce these checks locally.

Highlights
----------

- Study schemas for hypotheses, factors, blocking, admissible conditions, and replications
- Artifact contracts that connect runs, events, and evaluation outputs
- Reproducible condition materialization and execution helpers
- Runnable examples and recipes for study-definition workflows
- Documented composition seams for user code:
  ``design_research_problems.integration``,
  the stable ``design_research_agents.study`` facade, and the top-level
  ``design_research_analysis`` artifact API

The internal package adapters consume ``design_research_problems.integration``
and ``design_research_agents.integration``. The latter is a compatibility seam,
not the recommended authoring API; new user code should use
``design_research_agents.study``.

Typical Workflow
----------------

1. Define hypotheses, factors, blocking, and admissible conditions.
2. Materialize concrete study conditions and replication plans.
3. Execute runs across agents and problems while preserving artifact contracts.
4. Export standardized artifacts for downstream analysis and reporting.
5. Reuse examples and recipes to benchmark or extend the protocol.

.. container:: drc-home-callout

   .. note::

      **Start with** :doc:`quickstart` to define a first study, materialize a
      concrete condition set, and get into a reproducible local loop before
      branching into examples, recipes, and reference material. If you are
      integrating downstream tooling, keep :doc:`artifact_contract` open beside
      the quickstart so the public export guarantees stay explicit.

Guides
------

Learn the study-modeling concepts, setup flow, and orchestration patterns that
shape a stable experimental pipeline.

- :doc:`guides`
- :doc:`installation`
- :doc:`quickstart`
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
- :doc:`automation_baseline`

Architecture: Two Complementary Views
-------------------------------------

**Control topology:** Problems and Agents are peer study inputs. Experiments
owns study design and coordinates their execution, then defines the artifact
handoff to Analysis.

**Runtime and data flow:** Problems + Agents → Experiments artifact set →
Analysis → evidence that can refine the next study protocol.

These are two views of the same package family, not an installation order. The
umbrella routes imports and pins a tested combination; implementation stays
with the package that owns each behavior. See the umbrella
`compatibility and package status <https://cmudrc.github.io/design-research/compatibility.html>`_
for the tested family combination.

.. container:: drc-home-ecosystem

   .. image:: _static/ecosystem-platform.svg
      :alt: Two-view diagram showing the control topology and runtime data flow across Problems, Agents, Experiments, and Analysis.
      :class: dark-light drc-ecosystem-figure
      :width: 100%
      :align: center

Ecosystem Packages
------------------

- **Problems** — tasks, prompts, grammars, benchmarks, and evaluators:
  `documentation <https://cmudrc.github.io/design-research-problems/>`__
- **Agents** — AI participants, workflows, tools, and traceable reasoning:
  `documentation <https://cmudrc.github.io/design-research-agents/>`__
- **Experiments** — hypotheses, factors, conditions, replications, execution,
  and artifact export: :doc:`guides`
- **Analysis** — validation, transformation, statistics, and visualization of
  study artifacts:
  `documentation <https://cmudrc.github.io/design-research-analysis/>`__
- **Umbrella** — routed imports, learning paths, and tested compatibility:
  `documentation <https://cmudrc.github.io/design-research/>`__

Start Here
----------

- :doc:`guides`
- :doc:`installation`
- :doc:`quickstart`
- :doc:`concepts`
- :doc:`typical_workflow`
- :doc:`examples/index`
- :doc:`api`
- :doc:`artifact_contract`
- :doc:`vscode_start`
- :doc:`automation_baseline`
- `CONTRIBUTING.md <https://github.com/cmudrc/design-research-experiments/blob/HEAD/CONTRIBUTING.md>`_

.. toctree::
   :maxdepth: 2
   :caption: Guides
   :hidden:

   guides

.. toctree::
   :maxdepth: 2
   :caption: Examples
   :hidden:

   examples/index

.. toctree::
   :maxdepth: 2
   :caption: Reference
   :hidden:

   reference/index

.. toctree::
   :maxdepth: 1
   :caption: Development
   :hidden:

   CONTRIBUTING.md <https://github.com/cmudrc/design-research-experiments/blob/HEAD/CONTRIBUTING.md>
