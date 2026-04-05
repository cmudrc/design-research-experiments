Real Stack Interoperability
===========================

Source: ``examples/real_stack_interoperability.py``

Introduction
------------

Run one packaged problem from `design-research-problems` through a public
`design-research-agents` baseline and validate the exported `events.csv`
contract with `design-research-analysis`'s artifact-first integration API.

Technical Implementation
------------------------

1. Import the package-owned ``integration`` modules from installed sibling
   libraries.
2. Execute a one-run study that uses a packaged optimization problem together
   with `SeededRandomBaselineAgent`.
3. Export canonical artifacts and validate the event table through the analysis
   package's artifact-first integration contract.

.. literalinclude:: ../../../examples/real_stack_interoperability.py
   :language: python
   :lines: 20-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/real_stack_interoperability.py

Install the coordinated sibling packages first. This example now uses the
public package-owned seams directly and no longer bootstraps adjacent worktrees.

The script prints the packaged problem identity, one successful run result, and
the exported artifact filenames after the event table passes validation.
