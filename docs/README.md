# Documentation Maintenance

## Build Docs Locally

- `make docs-check`
- `make docs-build`

## Example Page Generation

Example pages are generated from runnable scripts via `scripts/generate_example_docs.py`.
Keep recipe and CLI examples synchronized with generated pages.

## Docstring Style

Use Google-style docstrings where policy applies.
Run `make docstrings-check` before merge.

## Page-Writing Conventions

- Keep homepages in this order: title, tagline, what it does, highlights, typical workflow, ecosystem integration, choose your path, start here.
- Keep the hidden home-page toctrees grouped as guides, examples, reference, then development so PyData navigation stays consistent across repos.
- Keep methodological framing explicit: this package encodes study logic, not just execution utilities.
- Use complete runnable snippets with visible outputs.

## Table vs Prose Rule

Prefer compact tables for scanning. Preserve nuance in narrative paragraphs directly below the table. Do not use tables to carry long explanatory sentences.

## Cross-links

Use `:doc:` for internal links and link to sibling ecosystem docs when describing adapters or artifact handoffs.

## API Page Updates

When public exports change, update:

- `docs/api.rst`
- concepts/workflow pages
- quickstart/examples snippets
