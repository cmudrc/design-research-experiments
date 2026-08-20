Installation
============

Package Install
---------------

.. code-block:: bash

   python -m pip install design-research-experiments

Editable Install
----------------

.. code-block:: bash

   git clone https://github.com/cmudrc/design-research-experiments.git
   cd design-research-experiments
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev]"

Maintainer Shortcut
-------------------

.. code-block:: bash

   make dev

Notes
-----

The experiments package keeps runtime dependencies deliberately small. User
code that composes the sibling packages directly should use
``design_research_problems.integration``, the stable
``design_research_agents.study`` facade, and the top-level
``design_research_analysis`` artifact API. Internally, its adapters consume
``design_research_problems.integration`` and
``design_research_agents.integration``; the latter remains a compatibility
seam, not the recommended authoring API. The package itself remains
the orchestration surface; there is intentionally no separate
``design_research_experiments.integration`` module. See
:doc:`dependencies_and_extras` for DOE and development extras plus
release-check guidance.
