Installation
============

Package Install
---------------

.. code-block:: bash

   pip install design-research-experiments

Editable Install
----------------

.. code-block:: bash

   git clone https://github.com/cmudrc/design-research-experiments.git
   cd design-research-experiments
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -e ".[dev]"

Maintainer Shortcut
-------------------

.. code-block:: bash

   make dev

Notes
-----

 The experiments package keeps runtime dependencies deliberately small and
 delegates optional sibling interoperability to
 ``design_research_problems.integration``,
 ``design_research_agents.integration``, and
 ``design_research_analysis.integration``. The package itself remains the
 orchestration surface; there is intentionally no separate
 ``design_research_experiments.integration`` module. See
 :doc:`dependencies_and_extras` for development extras and release-check
 guidance.
