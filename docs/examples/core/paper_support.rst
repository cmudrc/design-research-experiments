Paper Support
=============

Source: ``examples/paper_support.py``

Introduction
------------

Run a tiny offline study, aggregate component-owned contributions with durable
run evidence, then explicitly export both the support contract and a compilable
paper draft. No paper files are written by ``run_study`` or collection alone.

Technical Implementation
------------------------

The example passes a versioned JSON-compatible component packet to
``collect_paper_support``. The same packet and artifact root are passed to
``export_paper_draft``, which is called separately with explicit overwrite and
completeness requirements. Strict failures expose ``PaperDraftIncompleteError``.

.. literalinclude:: ../../../examples/paper_support.py
   :language: python
   :lines: 20-
   :linenos:

Expected Results
----------------

.. rubric:: Run Command

.. code-block:: bash

   PYTHONPATH=src python examples/paper_support.py

The script records two successful run-evidence directories, writes the support
files, and assembles ``main.tex``, Markdown, sections, references, and a draft
manifest beneath ``artifacts/example-paper-support/paper-draft``.
