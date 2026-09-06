Paper Support
=============

Source: ``examples/paper_support.py``

Introduction
------------

Run a tiny offline study, aggregate one component-owned citation and background
blurb with the durable run evidence, then explicitly export paper-draft support.
No paper files are written by ``run_study`` or ``collect_paper_support``.

Technical Implementation
------------------------

The example passes a versioned JSON-compatible component packet to
``collect_paper_support``. The packet carries one curated BibTeX record and
evidence-linked contributions. ``export_paper_support`` is called separately
with explicit overwrite permission.

.. literalinclude:: ../../../examples/paper_support.py
   :language: python
   :lines: 20-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/paper_support.py

The script records two successful run-evidence directories and writes
``paper_support.json``, ``paper_outline.md``, ``references.json``, and
``references.bib`` beneath ``artifacts/example-paper-support/artifacts/paper-draft``.
