Reporting and Exports
=====================

These helpers convert completed study artifacts into downstream-friendly tables
and lightweight narrative outputs. They are intentionally simple: the package
aims to make the canonical data products easy to export, then provide small
helpers for summaries and manuscript scaffolding on top of those exports.

Use :func:`design_research_experiments.export_analysis_tables` when you need the
stable tabular interface for other tools. Use the rendering helpers when you
need a human-readable summary in markdown or plain text.

.. currentmodule:: design_research_experiments

Canonical Table Exports
-----------------------

.. autosummary::
   :nosignatures:

   export_analysis_tables

.. autofunction:: export_analysis_tables

Narrative and Report Helpers
----------------------------

.. autosummary::
   :nosignatures:

   render_markdown_summary
   render_methods_scaffold
   render_codebook
   render_significance_brief
   write_markdown_report

.. autofunction:: render_markdown_summary

.. autofunction:: render_methods_scaffold

.. autofunction:: render_codebook

.. autofunction:: render_significance_brief

.. autofunction:: write_markdown_report
