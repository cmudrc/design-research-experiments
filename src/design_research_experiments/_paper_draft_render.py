"""Deterministic Markdown and LaTeX rendering for paper drafts."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .paper import ContributionKind, EvidenceBasis, PaperContribution, PaperSection, PaperSupport
from .schemas import ValidationError
from .study import Study

AUTHOR_REVIEW_LABEL = "Generated paper draft. Author review required."
_CITATION_KEY = re.compile(r"^[A-Za-z0-9_.:-]+$")


def render_draft_files(
    study: Study,
    support: PaperSupport,
    *,
    asset_paths: Mapping[str, Path],
) -> dict[Path, str]:
    """Return every generated text file keyed by draft-relative path."""
    resolved_citations = _resolved_citation_keys(support.references)
    sections = {
        section: _render_latex_section(
            study,
            support,
            section=section,
            resolved_citations=resolved_citations,
            asset_paths=asset_paths,
        )
        for section in PaperSection
    }
    files = {
        Path("main.tex"): _render_main_tex(study, resolved_citations=resolved_citations),
        Path("paper_draft.md"): _render_markdown(
            study,
            support,
            resolved_citations=resolved_citations,
            asset_paths=asset_paths,
        ),
        Path("references.bib"): render_references_bib(support.references),
        Path("README.md"): _render_readme(),
    }
    files.update(
        {Path("sections") / f"{section.value}.tex": text for section, text in sections.items()}
    )
    return files


def render_references_bib(references: Sequence[Mapping[str, Any]]) -> str:
    """Render only user-curated BibTeX records without inferring fields."""
    entries = [
        str(reference["raw_text"]).strip()
        for reference in references
        if isinstance(reference.get("raw_text"), str)
        and str(reference["raw_text"]).lstrip().startswith("@")
    ]
    return "" if not entries else "\n\n".join(entries) + "\n"


def latex_escape(value: object) -> str:
    """Escape arbitrary plain text for safe inclusion in LaTeX."""
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "\N{EN DASH}": "--",
        "\N{EM DASH}": "---",
        "\N{LEFT SINGLE QUOTATION MARK}": "`",
        "\N{RIGHT SINGLE QUOTATION MARK}": "'",
        "\N{LEFT DOUBLE QUOTATION MARK}": "``",
        "\N{RIGHT DOUBLE QUOTATION MARK}": "''",
        "\N{GREEK SMALL LETTER ALPHA}": r"$\alpha$",
        "\N{GREEK SMALL LETTER BETA}": r"$\beta$",
        "\N{GREEK SMALL LETTER GAMMA}": r"$\gamma$",
        "\N{GREEK SMALL LETTER MU}": r"$\mu$",
    }
    return "".join(replacements.get(character, character) for character in str(value))


def _render_main_tex(study: Study, *, resolved_citations: set[str]) -> str:
    """Render the top-level compilable LaTeX document."""
    authors = ", ".join(study.authors) if study.authors else "TODO: Confirm author list"
    bibliography = ""
    if resolved_citations:
        bibliography = "\n\\bibliographystyle{plain}\n\\bibliography{references}\n"
    return (
        "\\documentclass[11pt]{article}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage[hidelinks]{hyperref}\n"
        "\\usepackage[margin=1in]{geometry}\n"
        f"\\title{{{latex_escape(study.title)}}}\n"
        f"\\author{{{latex_escape(authors)}}}\n"
        "\\date{}\n"
        "\\begin{document}\n"
        f"\\noindent\\fbox{{\\textbf{{{AUTHOR_REVIEW_LABEL}}}}}\\par\\medskip\n"
        "\\maketitle\n"
        "\\input{sections/introduction}\n"
        "\\input{sections/background}\n"
        "\\input{sections/methods}\n"
        "\\input{sections/results}\n"
        "\\input{sections/discussion}\n"
        f"{bibliography}"
        "\\end{document}\n"
    )


def _render_latex_section(
    study: Study,
    support: PaperSupport,
    *,
    section: PaperSection,
    resolved_citations: set[str],
    asset_paths: Mapping[str, Path],
) -> str:
    """Render one LaTeX section from supported facts and TODOs."""
    lines = [f"\\section{{{section.value.title()}}}", ""]
    if section == PaperSection.INTRODUCTION:
        lines.extend(_latex_introduction(study))
    contributions = [item for item in support.contributions if item.section == section]
    if section == PaperSection.BACKGROUND and not contributions:
        lines.append(_latex_todo("Add author-curated background and prior-work context."))
    for contribution in contributions:
        lines.extend(
            _latex_contribution(
                contribution,
                resolved_citations=resolved_citations,
                asset_path=asset_paths.get(contribution.contribution_id),
            )
        )
    if section == PaperSection.DISCUSSION:
        lines.extend(_latex_discussion(study, support.contributions))
    for gap in support.reporting_gaps:
        if gap.section == section:
            lines.append(_latex_todo(gap.message))
    lines.extend(_section_author_todos(section))
    return "\n".join(lines).rstrip() + "\n"


def _latex_introduction(study: Study) -> list[str]:
    """Render explicit study framing without synthesizing novelty claims."""
    lines = [latex_escape(study.description)]
    if study.rationale:
        lines.extend(["", latex_escape(study.rationale)])
    if study.hypotheses:
        lines.extend(["", "\\subsection{Study hypotheses}", "\\begin{itemize}"])
        lines.extend(
            f"\\item \\textbf{{{latex_escape(item.label)}}}: {latex_escape(item.statement)}"
            for item in study.hypotheses
        )
        lines.append("\\end{itemize}")
    return lines


def _latex_contribution(
    contribution: PaperContribution,
    *,
    resolved_citations: set[str],
    asset_path: Path | None,
) -> list[str]:
    """Render one evidence-labeled contribution and optional retained asset."""
    prefix = {
        EvidenceBasis.CONFIGURED: "The study configuration specifies: ",
        EvidenceBasis.OBSERVED: "Retained execution evidence shows: ",
        EvidenceBasis.ANALYZED: "The executed analysis record reports: ",
        EvidenceBasis.USER: "User-supplied statement: ",
    }[contribution.evidence_basis]
    citation_text, citation_todos = _latex_citations(contribution, resolved_citations)
    body = f"{latex_escape(prefix + contribution.text)}{citation_text}"
    if contribution.kind == ContributionKind.BULLET:
        lines = ["\\begin{itemize}", f"\\item {body}", "\\end{itemize}"]
    else:
        lines = [body]
    if asset_path is not None and contribution.kind == ContributionKind.FIGURE:
        lines.extend(
            [
                "\\begin{figure}[htbp]",
                "\\centering",
                f"\\includegraphics[width=0.9\\linewidth]{{{asset_path.as_posix()}}}",
                f"\\caption{{{latex_escape(contribution.text)}}}",
                "\\end{figure}",
            ]
        )
    if asset_path is not None and contribution.kind == ContributionKind.TABLE:
        if asset_path.suffix.lower() == ".tex":
            lines.append(f"\\input{{{asset_path.with_suffix('').as_posix()}}}")
        else:
            lines.append(
                _latex_todo(f"Format retained table asset {asset_path.as_posix()} for LaTeX.")
            )
    lines.extend(_latex_todo(todo) for todo in citation_todos)
    return ["", *lines]


def _latex_citations(
    contribution: PaperContribution,
    resolved_citations: set[str],
) -> tuple[str, list[str]]:
    """Split curated LaTeX citations from visible missing-citation TODOs."""
    valid: list[str] = []
    todos: list[str] = []
    for key in contribution.citation_keys:
        if not _CITATION_KEY.fullmatch(key):
            raise ValidationError(f"Citation key {key!r} is unsafe for LaTeX.")
        if key in resolved_citations:
            valid.append(key)
        else:
            todos.append(f"Add curated BibTeX for citation {key!r} before citing it.")
    citation_text = "" if not valid else f" \\cite{{{','.join(valid)}}}"
    return citation_text, todos


def _latex_discussion(
    study: Study,
    contributions: Sequence[PaperContribution],
) -> list[str]:
    """Render hypothesis-scoped factual recaps and interpretation TODOs."""
    lines: list[str] = []
    for hypothesis in study.hypotheses:
        linked = _hypothesis_evidence(contributions, hypothesis.hypothesis_id)
        lines.extend(["", f"\\subsection{{{latex_escape(hypothesis.label)}}}"])
        if linked:
            lines.extend(latex_escape(f"Evidence recap: {item.text}") for item in linked)
        else:
            lines.append(_latex_todo("Add an evidence-backed recap for this hypothesis."))
        lines.append(_latex_todo("Interpret the evidence for this hypothesis."))
    return lines


def _section_author_todos(section: PaperSection) -> list[str]:
    """Return LaTeX author-judgment TODOs for one manuscript section."""
    todos = {
        PaperSection.INTRODUCTION: (
            "Establish the broader literature context and literature gap.",
            "State the intended contribution and novelty after author review.",
        ),
        PaperSection.BACKGROUND: (
            "Synthesize the modular sources into an author-reviewed argument.",
        ),
        PaperSection.METHODS: (),
        PaperSection.RESULTS: ("Verify table and figure ordering against the analysis record.",),
        PaperSection.DISCUSSION: (
            "Explain implications and limitations.",
            "Compare findings with prior work.",
            "Specify future work.",
        ),
    }[section]
    return ["", *(_latex_todo(todo) for todo in todos)] if todos else []


def _latex_todo(message: str) -> str:
    """Render one visibly marked LaTeX author-review TODO."""
    return f"\\noindent\\textbf{{TODO (author review):}} {latex_escape(message)}\\par"


def _render_markdown(
    study: Study,
    support: PaperSupport,
    *,
    resolved_citations: set[str],
    asset_paths: Mapping[str, Path],
) -> str:
    """Render the complete Markdown companion draft."""
    lines = [f"> **{AUTHOR_REVIEW_LABEL}**", "", f"# {study.title}"]
    for section in PaperSection:
        lines.extend(["", f"## {section.value.title()}"])
        if section == PaperSection.INTRODUCTION:
            lines.extend(["", study.description])
            if study.rationale:
                lines.extend(["", study.rationale])
            if study.hypotheses:
                lines.extend(["", "### Study hypotheses", ""])
                lines.extend(f"- **{item.label}:** {item.statement}" for item in study.hypotheses)
        contributions = [item for item in support.contributions if item.section == section]
        if section == PaperSection.BACKGROUND and not contributions:
            lines.extend(
                [
                    "",
                    "- [ ] **TODO (author review):** Add author-curated background "
                    "and prior-work context.",
                ]
            )
        for item in contributions:
            citations = " ".join(
                f"[@{key}]" for key in item.citation_keys if key in resolved_citations
            )
            source = (
                f"{item.evidence_basis.value}; {item.source.package}:{item.source.component_id}"
            )
            lines.extend(
                ["", f"- {item.text}{(' ' + citations) if citations else ''} _[{source}]_"]
            )
            if item.contribution_id in asset_paths:
                lines.append(
                    f"  - Retained asset: `{asset_paths[item.contribution_id].as_posix()}`"
                )
            for key in item.citation_keys:
                if key not in resolved_citations:
                    lines.append(
                        f"  - TODO: Add curated BibTeX for citation `{key}` before citing it."
                    )
        for gap in support.reporting_gaps:
            if gap.section == section:
                lines.extend(["", f"- [ ] **TODO (evidence):** {gap.message}"])
        if section == PaperSection.DISCUSSION:
            lines.extend(_markdown_discussion(study, support.contributions))
        for todo in _plain_author_todos(section):
            lines.extend(["", f"- [ ] **TODO (author review):** {todo}"])
    lines.extend(["", "## Run accounting", ""])
    lines.extend(
        f"- {key.replace('_', ' ').title()}: {value}"
        for key, value in support.run_accounting.items()
    )
    return "\n".join(lines).rstrip() + "\n"


def _plain_author_todos(section: PaperSection) -> tuple[str, ...]:
    """Return Markdown author-judgment TODOs for one manuscript section."""
    return {
        PaperSection.INTRODUCTION: (
            "Establish the broader literature context and literature gap.",
            "State the intended contribution and novelty after author review.",
        ),
        PaperSection.BACKGROUND: (
            "Synthesize the modular sources into an author-reviewed argument.",
        ),
        PaperSection.METHODS: (),
        PaperSection.RESULTS: ("Verify table and figure ordering against the analysis record.",),
        PaperSection.DISCUSSION: (
            "Explain implications and limitations.",
            "Compare findings with prior work.",
            "Specify future work.",
        ),
    }[section]


def _markdown_discussion(
    study: Study,
    contributions: Sequence[PaperContribution],
) -> list[str]:
    """Render Markdown hypothesis recaps without interpreting results."""
    lines: list[str] = []
    for hypothesis in study.hypotheses:
        linked = _hypothesis_evidence(contributions, hypothesis.hypothesis_id)
        lines.extend(["", f"### {hypothesis.label}", ""])
        if linked:
            lines.extend(f"- Evidence recap: {item.text}" for item in linked)
        else:
            lines.append("- [ ] **TODO (author review):** Add an evidence-backed recap.")
        lines.append("- [ ] **TODO (author review):** Interpret this evidence.")
    return lines


def _hypothesis_evidence(
    contributions: Sequence[PaperContribution],
    hypothesis_id: str,
) -> list[PaperContribution]:
    """Find observed or analyzed evidence explicitly linked to a hypothesis."""
    return [
        item
        for item in contributions
        if hypothesis_id in _metadata_strings(item.metadata.get("hypothesis_ids"))
        and item.evidence_basis in {EvidenceBasis.OBSERVED, EvidenceBasis.ANALYZED}
    ]


def _resolved_citation_keys(references: Sequence[Mapping[str, Any]]) -> set[str]:
    """Return keys backed by caller-supplied raw BibTeX records."""
    return {
        str(reference["key"])
        for reference in references
        if isinstance(reference.get("raw_text"), str)
        and str(reference["raw_text"]).lstrip().startswith("@")
    }


def _metadata_strings(value: Any) -> tuple[str, ...]:
    """Normalize a metadata array to strings without accepting scalar text."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _render_readme() -> str:
    """Render compilation and review-boundary guidance for the draft."""
    return f"""# Generated paper draft

{AUTHOR_REVIEW_LABEL}

This directory was created by an explicit paper-draft export. Configured,
observed, analyzed, and user-supplied statements remain visibly distinct.
TODOs mark missing evidence or interpretation that requires an author.

Compile the LaTeX draft from this directory with:

```bash
tectonic main.tex
```

The generated files are a review artifact, not a submitted manuscript and not
an assertion that planned analyses were executed.
"""
