Real Stack Interoperability
===========================

Source: ``examples/real_stack_interoperability.py``

Introduction
------------

Run one packaged problem from `design-research-problems` through a public
`design-research-agents` baseline and validate the exported `events.csv`
contract with `design-research-analysis`'s artifact-first helpers.

Technical Implementation
------------------------

Install the exact sibling versions from the tested package family before using
the source-checkout run command:

.. code-block:: bash

   python -m pip install "design-research-problems==0.4.0" \
       "design-research-agents==0.6.0" \
       "design-research-analysis==0.3.1"

1. Import those installed sibling libraries through their package-level APIs.
2. Execute a one-run study that uses a packaged optimization problem together
   with `SeededRandomBaselineAgent`.
3. Export canonical artifacts and validate the event table through the analysis
   package's artifact-first helpers.

.. literalinclude:: ../../../examples/real_stack_interoperability.py
   :language: python
   :lines: 29-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/real_stack_interoperability.py

The script prints the packaged problem identity, one successful run result, and
the exported artifact filenames after the event table passes validation.
