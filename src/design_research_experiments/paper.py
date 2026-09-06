"""Deterministic paper-draft contributions assembled from study evidence."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, cast

from .evidence import load_run_evidence_records
from .io import json_io
from .schemas import ValidationError, stable_json_dumps, to_jsonable
from .study import Study

PAPER_DRAFT_CONTRACT_VERSION = "0.1.0"
PAPER_DRAFT_STATUS = "deterministic-scaffold-not-a-manuscript"


class PaperSection(StrEnum):
    """Supported sections for deterministic paper contributions."""

    INTRODUCTION = "introduction"
    BACKGROUND = "background"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"


class ContributionKind(StrEnum):
    """Supported presentation forms for one contribution."""

    PARAGRAPH = "paragraph"
    BULLET = "bullet"
    FIGURE = "figure"
    TABLE = "table"


class EvidenceBasis(StrEnum):
    """Evidence boundary associated with one contribution."""

    CONFIGURED = "configured"
    OBSERVED = "observed"
    ANALYZED = "analyzed"
    USER = "user"


@dataclass(frozen=True, slots=True)
class ContributionSource:
    """Package-owned source of one paper contribution packet."""

    package: str
    package_version: str
    component_type: str
    component_id: str

    def __post_init__(self) -> None:
        """Require stable provenance fields."""
        for field_name in ("package", "package_version", "component_type", "component_id"):
            if not str(getattr(self, field_name)).strip():
                raise ValidationError(f"Paper contribution source {field_name} must be non-empty.")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ContributionSource:
        """Build a source from a JSON-compatible mapping."""
        return cls(
            package=_required_text(payload, "package", context="paper contribution source"),
            package_version=_required_text(
                payload,
                "package_version",
                context="paper contribution source",
            ),
            component_type=_required_text(
                payload,
                "component_type",
                context="paper contribution source",
            ),
            component_id=_required_text(
                payload,
                "component_id",
                context="paper contribution source",
            ),
        )

    def to_dict(self) -> dict[str, str]:
        """Return the stable JSON representation."""
        return {
            "package": self.package,
            "package_version": self.package_version,
            "component_type": self.component_type,
            "component_id": self.component_id,
        }


@dataclass(frozen=True, slots=True)
class PaperContribution:
    """One factual blurb, bullet, figure, or table suggestion."""

    contribution_id: str
    section: PaperSection
    kind: ContributionKind
    text: str
    evidence_basis: EvidenceBasis
    source: ContributionSource
    citation_keys: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Require stable identity and evidence links for execution claims."""
        if not isinstance(self.section, PaperSection):
            raise ValidationError("Paper contribution section must be a PaperSection value.")
        if not isinstance(self.kind, ContributionKind):
            raise ValidationError("Paper contribution kind must be a ContributionKind value.")
        if not isinstance(self.evidence_basis, EvidenceBasis):
            raise ValidationError(
                "Paper contribution evidence_basis must be an EvidenceBasis value."
            )
        if not self.contribution_id.strip():
            raise ValidationError("Paper contribution contribution_id must be non-empty.")
        if not self.text.strip():
            raise ValidationError("Paper contribution text must be non-empty.")
        if self.evidence_basis in {EvidenceBasis.OBSERVED, EvidenceBasis.ANALYZED} and not (
            self.evidence_refs
        ):
            raise ValidationError(
                "Observed and analyzed paper contributions require at least one evidence_ref."
            )

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
        *,
        source: ContributionSource,
    ) -> PaperContribution:
        """Build and validate one contribution from a component packet."""
        return cls(
            contribution_id=_required_text(
                payload,
                "contribution_id",
                context="paper contribution",
            ),
            section=_coerce_enum(
                PaperSection,
                payload.get("section"),
                field_name="paper contribution section",
            ),
            kind=_coerce_enum(
                ContributionKind,
                payload.get("kind"),
                field_name="paper contribution kind",
            ),
            text=_required_text(payload, "text", context="paper contribution"),
            evidence_basis=_coerce_enum(
                EvidenceBasis,
                payload.get("evidence_basis"),
                field_name="paper contribution evidence_basis",
            ),
            source=source,
            citation_keys=_string_tuple(
                payload.get("citation_keys", ()),
                field_name="citation_keys",
            ),
            evidence_refs=_string_tuple(
                payload.get("evidence_refs", ()),
                field_name="evidence_refs",
            ),
            metadata=_mapping(payload.get("metadata", {}), field_name="metadata"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the stable JSON representation."""
        return {
            "contribution_id": self.contribution_id,
            "section": self.section.value,
            "kind": self.kind.value,
            "text": self.text,
            "evidence_basis": self.evidence_basis.value,
            "source": self.source.to_dict(),
            "citation_keys": list(self.citation_keys),
            "evidence_refs": list(self.evidence_refs),
            "metadata": to_jsonable(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ReportingGap:
    """One unresolved fact that prevents a complete paper statement."""

    gap_id: str
    section: PaperSection
    message: str
    source: ContributionSource
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Require stable gap identity and an actionable message."""
        if not self.gap_id.strip():
            raise ValidationError("Reporting gap gap_id must be non-empty.")
        if not self.message.strip():
            raise ValidationError("Reporting gap message must be non-empty.")

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
        *,
        source: ContributionSource,
    ) -> ReportingGap:
        """Build and validate one reporting gap from a component packet."""
        return cls(
            gap_id=_required_text(payload, "gap_id", context="reporting gap"),
            section=_coerce_enum(
                PaperSection,
                payload.get("section"),
                field_name="reporting gap section",
            ),
            message=_required_text(payload, "message", context="reporting gap"),
            source=source,
            evidence_refs=_string_tuple(
                payload.get("evidence_refs", ()),
                field_name="evidence_refs",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the stable JSON representation."""
        return {
            "gap_id": self.gap_id,
            "section": self.section.value,
            "message": self.message,
            "source": self.source.to_dict(),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class PaperContributionPacket:
    """Versioned JSON boundary emitted by one component library."""

    source: ContributionSource
    contributions: tuple[PaperContribution, ...] = ()
    references: tuple[Mapping[str, Any], ...] = ()
    reporting_gaps: tuple[ReportingGap, ...] = ()
    schema_version: str = PAPER_DRAFT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        """Require one schema version and one source across the packet."""
        if self.schema_version != PAPER_DRAFT_CONTRACT_VERSION:
            raise ValidationError("Paper contribution packet uses an unsupported schema version.")
        if any(item.source != self.source for item in self.contributions):
            raise ValidationError(
                "Paper contribution packet contributions must share packet source."
            )
        if any(item.source != self.source for item in self.reporting_gaps):
            raise ValidationError("Paper contribution packet gaps must share packet source.")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> PaperContributionPacket:
        """Validate and normalize a JSON-compatible component packet."""
        schema_version = str(payload.get("schema_version", ""))
        if schema_version != PAPER_DRAFT_CONTRACT_VERSION:
            raise ValidationError(
                "Paper contribution packet schema_version "
                f"{schema_version!r} does not match {PAPER_DRAFT_CONTRACT_VERSION!r}."
            )
        source_payload = payload.get("source")
        if not isinstance(source_payload, Mapping):
            raise ValidationError("Paper contribution packet source must be a JSON object.")
        source = ContributionSource.from_mapping(source_payload)
        contributions = tuple(
            PaperContribution.from_mapping(item, source=source)
            for item in _mapping_sequence(payload.get("contributions", ()), "contributions")
        )
        reporting_gaps = tuple(
            ReportingGap.from_mapping(item, source=source)
            for item in _mapping_sequence(payload.get("reporting_gaps", ()), "reporting_gaps")
        )
        references = tuple(
            _normalize_reference(item)
            for item in _reference_sequence(payload.get("references", ()))
        )
        return cls(
            source=source,
            contributions=contributions,
            references=references,
            reporting_gaps=reporting_gaps,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the stable JSON representation."""
        return {
            "schema_version": self.schema_version,
            "source": self.source.to_dict(),
            "contributions": [item.to_dict() for item in self.contributions],
            "references": [to_jsonable(item) for item in self.references],
            "reporting_gaps": [item.to_dict() for item in self.reporting_gaps],
        }


@dataclass(frozen=True, slots=True)
class PaperSupport:
    """Deterministic aggregate used by later paper-draft renderers."""

    study_id: str
    run_accounting: Mapping[str, int]
    contributions: tuple[PaperContribution, ...]
    references: tuple[Mapping[str, Any], ...]
    reporting_gaps: tuple[ReportingGap, ...]
    schema_version: str = PAPER_DRAFT_CONTRACT_VERSION
    draft_status: str = PAPER_DRAFT_STATUS

    def to_dict(self) -> dict[str, Any]:
        """Return the stable JSON representation."""
        return {
            "schema_version": self.schema_version,
            "draft_status": self.draft_status,
            "study_id": self.study_id,
            "run_accounting": dict(self.run_accounting),
            "contributions": [item.to_dict() for item in self.contributions],
            "references": [to_jsonable(item) for item in self.references],
            "reporting_gaps": [item.to_dict() for item in self.reporting_gaps],
        }


def collect_paper_support(
    study_or_output: Study | str | Path,
    *,
    output_dir: str | Path | None = None,
    component_packets: Sequence[PaperContributionPacket | Mapping[str, Any]] = (),
    user_references: Sequence[Any] = (),
) -> PaperSupport:
    """Collect factual paper support without writing files or generating prose with an LLM."""
    study, resolved_output_dir = _resolve_study_and_output(study_or_output, output_dir=output_dir)
    evidence = load_run_evidence_records(resolved_output_dir)
    _validate_evidence_study_ids(study, evidence)
    packets = tuple(_coerce_packet(packet) for packet in component_packets)

    source = _experiments_source(study.study_id)
    contributions = _study_contributions(study, source=source)
    gaps: list[ReportingGap] = []
    references_with_sources: list[tuple[Mapping[str, Any], ContributionSource]] = []
    for packet in packets:
        contributions.extend(packet.contributions)
        gaps.extend(packet.reporting_gaps)
        references_with_sources.extend(
            (reference, packet.source) for reference in packet.references
        )

    user_source = ContributionSource(
        package="user",
        package_version="unversioned",
        component_type="reference-set",
        component_id=study.study_id,
    )
    references_with_sources.extend(
        (_normalize_reference(reference), user_source) for reference in user_references
    )

    run_accounting = _run_accounting(evidence, contributions=contributions)
    evidence_contribution = _evidence_contribution(
        study,
        evidence=evidence,
        run_accounting=run_accounting,
        source=source,
    )
    if evidence_contribution is not None:
        contributions.append(evidence_contribution)

    gaps.extend(
        _aggregate_reporting_gaps(
            study,
            evidence=evidence,
            run_accounting=run_accounting,
            packets=packets,
            contributions=contributions,
            source=source,
        )
    )
    deduplicated_contributions = _deduplicate_contributions(contributions)
    deduplicated_references = _deduplicate_references(references_with_sources)
    _validate_contribution_citations(deduplicated_contributions, deduplicated_references)
    gaps.extend(_bibtex_gaps(deduplicated_references, source=source))

    return PaperSupport(
        study_id=study.study_id,
        run_accounting=run_accounting,
        contributions=tuple(sorted(deduplicated_contributions, key=_contribution_sort_key)),
        references=tuple(sorted(deduplicated_references, key=lambda item: str(item["key"]))),
        reporting_gaps=tuple(sorted(_deduplicate_gaps(gaps), key=_gap_sort_key)),
    )


def export_paper_support(
    paper_support: PaperSupport,
    *,
    output_dir: str | Path,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Explicitly export deterministic support into a strongly marked paper-draft directory."""
    draft_dir = Path(output_dir) / "artifacts" / "paper-draft"
    if draft_dir.exists() and any(draft_dir.iterdir()) and not overwrite:
        raise ValidationError(
            f"Paper-draft directory already contains files: {draft_dir}. Pass overwrite=True."
        )
    draft_dir.mkdir(parents=True, exist_ok=True)

    support_path = json_io.write_json(draft_dir / "paper_support.json", paper_support.to_dict())
    references_path = json_io.write_json(
        draft_dir / "references.json",
        [to_jsonable(reference) for reference in paper_support.references],
    )
    outline_path = draft_dir / "paper_outline.md"
    outline_path.write_text(render_paper_support_markdown(paper_support), encoding="utf-8")
    bib_path = draft_dir / "references.bib"
    bib_path.write_text(_render_references_bib(paper_support.references), encoding="utf-8")

    return {
        "paper_support.json": support_path,
        "paper_outline.md": outline_path,
        "references.json": references_path,
        "references.bib": bib_path,
    }


def render_paper_support_markdown(paper_support: PaperSupport) -> str:
    """Render factual contribution scaffolding with visible evidence labels and TODO gaps."""
    lines = [
        "# PAPER DRAFT SUPPORT — NOT A MANUSCRIPT",
        "",
        "This deterministic scaffold contains evidence-linked facts and unresolved TODOs. "
        "It does not assert scientific conclusions or replace author review.",
    ]
    for section in PaperSection:
        lines.extend(["", f"## {section.value.title()}"])
        section_contributions = [
            contribution
            for contribution in paper_support.contributions
            if contribution.section == section
        ]
        if not section_contributions:
            lines.append("- _No supported contribution available._")
            continue
        for contribution in section_contributions:
            citations = ""
            if contribution.citation_keys:
                citations = " " + " ".join(f"[@{key}]" for key in contribution.citation_keys)
            source = contribution.source
            provenance = (
                f"{contribution.evidence_basis.value}; "
                f"{source.package}:{source.component_type}:{source.component_id}"
            )
            kind_prefix = (
                f"**{contribution.kind.value.title()}:** "
                if contribution.kind in {ContributionKind.FIGURE, ContributionKind.TABLE}
                else ""
            )
            lines.append(f"- {kind_prefix}{contribution.text}{citations} _[{provenance}]_")

    lines.extend(["", "## Reporting TODOs"])
    if not paper_support.reporting_gaps:
        lines.append("- [x] No unresolved reporting gaps recorded.")
    else:
        for gap in paper_support.reporting_gaps:
            lines.append(f"- [ ] **{gap.section.value.title()}:** {gap.message}")

    lines.extend(
        [
            "",
            "## Run Accounting",
            "",
        ]
    )
    for key, value in paper_support.run_accounting.items():
        lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    return "\n".join(lines) + "\n"


def _resolve_study_and_output(
    study_or_output: Study | str | Path,
    *,
    output_dir: str | Path | None,
) -> tuple[Study, Path]:
    """Resolve a live study or a portable canonical study directory."""
    if isinstance(study_or_output, Study):
        resolved = Path(
            output_dir or study_or_output.output_dir or Path("artifacts") / study_or_output.study_id
        )
        return study_or_output, resolved

    source_path = Path(study_or_output)
    if source_path.is_dir():
        study_path = source_path / "study.yaml"
        return Study.from_yaml(study_path), Path(output_dir or source_path)
    if source_path.name == "manifest.json":
        artifact_root = source_path.parent
        return Study.from_yaml(artifact_root / "study.yaml"), Path(output_dir or artifact_root)
    if source_path.suffix.lower() == ".json":
        return Study.from_json(source_path), Path(output_dir or source_path.parent)
    return Study.from_yaml(source_path), Path(output_dir or source_path.parent)


def _study_contributions(study: Study, *, source: ContributionSource) -> list[PaperContribution]:
    """Translate explicit study configuration into factual paper contributions."""
    contributions = [
        PaperContribution(
            contribution_id="experiments:study-design",
            section=PaperSection.METHODS,
            kind=ContributionKind.PARAGRAPH,
            text=(
                f"The configured study used a {study.design_spec.kind.value.replace('_', ' ')} "
                f"design with {_count_phrase(len(study.factors), 'factor')}, "
                f"{_count_phrase(len(study.blocks), 'block')}, and "
                f"{_count_phrase(study.run_budget.replicates, 'planned replicate')} per condition."
            ),
            evidence_basis=EvidenceBasis.CONFIGURED,
            source=source,
            evidence_refs=("study.yaml#/design_spec", "study.yaml#/run_budget"),
            metadata={"outline_order": 10},
        ),
        PaperContribution(
            contribution_id="experiments:seed-policy",
            section=PaperSection.METHODS,
            kind=ContributionKind.BULLET,
            text=(
                f"Random seeds were configured with the {study.seed_policy.strategy!r} strategy "
                f"and base seed {study.seed_policy.base_seed}."
            ),
            evidence_basis=EvidenceBasis.CONFIGURED,
            source=source,
            evidence_refs=("study.yaml#/seed_policy",),
            metadata={"outline_order": 30},
        ),
    ]
    contributions.extend(
        PaperContribution(
            contribution_id=f"experiments:hypothesis:{hypothesis.hypothesis_id}",
            section=PaperSection.INTRODUCTION,
            kind=ContributionKind.BULLET,
            text=f"Hypothesis {hypothesis.hypothesis_id}: {hypothesis.statement}",
            evidence_basis=EvidenceBasis.CONFIGURED,
            source=source,
            evidence_refs=(f"hypotheses.json#/{index}",),
        )
        for index, hypothesis in enumerate(study.hypotheses)
    )
    contributions.extend(
        PaperContribution(
            contribution_id=f"experiments:factor:{factor.name}",
            section=PaperSection.METHODS,
            kind=ContributionKind.BULLET,
            text=(
                f"Factor {factor.name!r} was configured as {factor.kind.value}, with levels "
                f"{', '.join(level.name for level in factor.levels)}."
            ),
            evidence_basis=EvidenceBasis.CONFIGURED,
            source=source,
            evidence_refs=(f"study.yaml#/factors/{index}",),
            metadata={"outline_order": 20},
        )
        for index, factor in enumerate(study.factors)
    )
    contributions.extend(
        PaperContribution(
            contribution_id=f"experiments:analysis-plan:{plan.analysis_plan_id}",
            section=PaperSection.METHODS,
            kind=ContributionKind.BULLET,
            text=(
                f"Analysis plan {plan.analysis_plan_id!r} configured the following test(s): "
                f"{', '.join(plan.tests) if plan.tests else 'none specified'}."
            ),
            evidence_basis=EvidenceBasis.CONFIGURED,
            source=source,
            evidence_refs=(f"analysis_plan.json#/{index}",),
            metadata={"outline_order": 50},
        )
        for index, plan in enumerate(study.analysis_plans)
    )
    return contributions


def _evidence_contribution(
    study: Study,
    *,
    evidence: Mapping[str, Mapping[str, Any]],
    run_accounting: Mapping[str, int],
    source: ContributionSource,
) -> PaperContribution | None:
    """Render the observed run-accounting sentence only when evidence exists."""
    if not evidence:
        return None
    analysis_accounting = ""
    if run_accounting["analyzed"] or run_accounting["excluded"]:
        analysis_accounting = (
            " Supplied analysis records identify "
            f"{_count_phrase(run_accounting['analyzed'], 'analyzed run')} and "
            f"{_count_phrase(run_accounting['excluded'], 'documented excluded run')}."
        )
    return PaperContribution(
        contribution_id="experiments:observed-run-accounting",
        section=PaperSection.METHODS,
        kind=ContributionKind.PARAGRAPH,
        text=(
            "The exported evidence accounts for "
            f"{_count_phrase(run_accounting['planned'], 'planned run')}: "
            f"{run_accounting['successful']} successful, {run_accounting['failed']} failed, "
            f"{run_accounting['skipped']} skipped, and {run_accounting['incomplete']} incomplete."
            f"{analysis_accounting}"
        ),
        evidence_basis=EvidenceBasis.OBSERVED,
        source=source,
        evidence_refs=tuple(f"artifacts/runs/{run_id}/run.json" for run_id in sorted(evidence)),
        metadata={"study_id": study.study_id, "outline_order": 40},
    )


def _aggregate_reporting_gaps(
    study: Study,
    *,
    evidence: Mapping[str, Mapping[str, Any]],
    run_accounting: Mapping[str, int],
    packets: Sequence[PaperContributionPacket],
    contributions: Sequence[PaperContribution],
    source: ContributionSource,
) -> list[ReportingGap]:
    """Create explicit gaps for facts the aggregator cannot honestly assert."""
    gaps: list[ReportingGap] = []
    if not evidence:
        gaps.append(
            ReportingGap(
                gap_id="experiments:missing-run-evidence",
                section=PaperSection.METHODS,
                message="No durable run evidence was found; execution claims remain unresolved.",
                source=source,
            )
        )
    if run_accounting["incomplete"]:
        gaps.append(
            ReportingGap(
                gap_id="experiments:incomplete-runs",
                section=PaperSection.METHODS,
                message=(
                    "Resolve or explain "
                    f"{_count_phrase(run_accounting['incomplete'], 'planned run')} without a "
                    "terminal outcome."
                ),
                source=source,
            )
        )
    if run_accounting["failed"]:
        gaps.append(
            ReportingGap(
                gap_id="experiments:failed-runs",
                section=PaperSection.RESULTS,
                message=(
                    "Explain the treatment of "
                    f"{_count_phrase(run_accounting['failed'], 'failed run')} using "
                    f"{'its' if run_accounting['failed'] == 1 else 'their'} recorded failure "
                    "reasons."
                ),
                source=source,
            )
        )
    if run_accounting["skipped"]:
        gaps.append(
            ReportingGap(
                gap_id="experiments:skipped-runs",
                section=PaperSection.RESULTS,
                message=(
                    f"Explain why {_count_phrase(run_accounting['skipped'], 'planned run')} "
                    f"{'was' if run_accounting['skipped'] == 1 else 'were'} skipped."
                ),
                source=source,
            )
        )

    has_problem_contributions = any(
        packet.source.package == "design-research-problems"
        or packet.source.component_type == "problem"
        for packet in packets
    )
    if study.problem_ids and not has_problem_contributions:
        gaps.append(
            ReportingGap(
                gap_id="experiments:missing-problem-contributions",
                section=PaperSection.BACKGROUND,
                message="Problem citations and prompt-lineage contributions were not supplied.",
                source=source,
            )
        )
    has_agent_contributions = any(
        packet.source.package == "design-research-agents"
        or packet.source.component_type
        in {"agent", "workflow", "pattern", "tool", "toolbox", "model-selector", "tracer"}
        for packet in packets
    )
    if study.agent_specs and not has_agent_contributions:
        gaps.append(
            ReportingGap(
                gap_id="experiments:missing-agent-contributions",
                section=PaperSection.METHODS,
                message=(
                    "Agent, workflow, model, and tool reporting contributions were not supplied."
                ),
                source=source,
            )
        )
    has_analyzed_contribution = any(
        contribution.evidence_basis == EvidenceBasis.ANALYZED for contribution in contributions
    )
    if study.analysis_plans and not has_analyzed_contribution:
        gaps.append(
            ReportingGap(
                gap_id="experiments:analysis-not-observed",
                section=PaperSection.RESULTS,
                message=(
                    "Analysis was configured, but no analyzed contribution establishes that a "
                    "planned method executed."
                ),
                source=source,
            )
        )
    return gaps


def _run_accounting(
    evidence: Mapping[str, Mapping[str, Any]],
    *,
    contributions: Sequence[PaperContribution] = (),
) -> dict[str, int]:
    """Summarize lifecycle facts and distinct analysis-accounting run IDs."""
    statuses = Counter(str(record["status"]) for record in evidence.values())
    analyzed_run_ids, excluded_run_ids = _analysis_run_ids(contributions)
    return {
        "planned": len(evidence),
        "attempted": sum(bool(record["attempted"]) for record in evidence.values()),
        "terminal": sum(bool(record["terminal"]) for record in evidence.values()),
        "successful": statuses["success"],
        "failed": statuses["failed"],
        "skipped": statuses["skipped"],
        "incomplete": statuses["pending"] + statuses["running"],
        "analyzed": len(analyzed_run_ids),
        "excluded": len(excluded_run_ids),
    }


def _analysis_run_ids(
    contributions: Sequence[PaperContribution],
) -> tuple[set[str], set[str]]:
    """Collect distinct included and documented-exclusion IDs from analyzed blocks."""
    analyzed: set[str] = set()
    excluded: set[str] = set()
    for contribution in contributions:
        if contribution.evidence_basis != EvidenceBasis.ANALYZED:
            continue
        included_rows = contribution.metadata.get("included_run_ids", ())
        if isinstance(included_rows, Sequence) and not isinstance(included_rows, (str, bytes)):
            analyzed.update(str(run_id) for run_id in included_rows if str(run_id).strip())
        exclusion_rows = contribution.metadata.get("exclusions", ())
        if not isinstance(exclusion_rows, Sequence) or isinstance(exclusion_rows, (str, bytes)):
            continue
        for row in exclusion_rows:
            if not isinstance(row, Mapping):
                continue
            run_id = str(row.get("run_id", "")).strip()
            if run_id:
                excluded.add(run_id)
    return analyzed, excluded


def _validate_evidence_study_ids(
    study: Study,
    evidence: Mapping[str, Mapping[str, Any]],
) -> None:
    """Reject accidental aggregation across study directories."""
    mismatched = sorted(
        run_id
        for run_id, record in evidence.items()
        if str(record.get("study_id")) != study.study_id
    )
    if mismatched:
        raise ValidationError(
            f"Run evidence does not belong to study {study.study_id!r}: {', '.join(mismatched)}."
        )


def _coerce_packet(
    packet: PaperContributionPacket | Mapping[str, Any],
) -> PaperContributionPacket:
    """Normalize typed and JSON-compatible packet inputs."""
    if isinstance(packet, PaperContributionPacket):
        return packet
    if not isinstance(packet, Mapping):
        raise ValidationError("Paper contribution packets must be objects or JSON mappings.")
    return PaperContributionPacket.from_mapping(packet)


def _deduplicate_contributions(
    contributions: Sequence[PaperContribution],
) -> list[PaperContribution]:
    """Deduplicate exact contributions and reject conflicting stable identifiers."""
    by_id: dict[str, PaperContribution] = {}
    for contribution in contributions:
        existing = by_id.get(contribution.contribution_id)
        if existing is None:
            by_id[contribution.contribution_id] = contribution
            continue
        if stable_json_dumps(existing.to_dict()) != stable_json_dumps(contribution.to_dict()):
            raise ValidationError(
                f"Conflicting paper contribution id: {contribution.contribution_id!r}."
            )
    return list(by_id.values())


def _deduplicate_gaps(gaps: Sequence[ReportingGap]) -> list[ReportingGap]:
    """Deduplicate exact gaps and reject conflicting stable identifiers."""
    by_id: dict[str, ReportingGap] = {}
    for gap in gaps:
        existing = by_id.get(gap.gap_id)
        if existing is None:
            by_id[gap.gap_id] = gap
            continue
        if stable_json_dumps(existing.to_dict()) != stable_json_dumps(gap.to_dict()):
            raise ValidationError(f"Conflicting reporting gap id: {gap.gap_id!r}.")
    return list(by_id.values())


def _deduplicate_references(
    references: Sequence[tuple[Mapping[str, Any], ContributionSource]],
) -> list[dict[str, Any]]:
    """Merge compatible citation records by stable key and retain package provenance."""
    by_key: dict[str, dict[str, Any]] = {}
    for raw_reference, source in references:
        reference = _normalize_reference(raw_reference)
        key = str(reference["key"])
        provenance = source.to_dict()
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = {**reference, "provenance": [provenance]}
            continue

        existing_fields = {
            field: value for field, value in existing.items() if field != "provenance"
        }
        for field_name in sorted(set(existing_fields) | set(reference)):
            old_value = existing_fields.get(field_name)
            new_value = reference.get(field_name)
            if old_value in (None, "", [], ()):
                existing[field_name] = new_value
            elif new_value not in (None, "", [], ()) and old_value != new_value:
                raise ValidationError(f"Conflicting citation key {key!r} for field {field_name!r}.")
        provenance_rows = cast(list[dict[str, str]], existing["provenance"])
        if provenance not in provenance_rows:
            provenance_rows.append(provenance)
            provenance_rows.sort(
                key=lambda item: (
                    item["package"],
                    item["component_type"],
                    item["component_id"],
                )
            )
    return list(by_key.values())


def _validate_contribution_citations(
    contributions: Sequence[PaperContribution],
    references: Sequence[Mapping[str, Any]],
) -> None:
    """Reject contribution citation keys that have no curated record."""
    available = {str(reference["key"]) for reference in references}
    missing = sorted(
        {
            citation_key
            for contribution in contributions
            for citation_key in contribution.citation_keys
            if citation_key not in available
        }
    )
    if missing:
        raise ValidationError(
            f"Paper contributions reference unknown citations: {', '.join(missing)}."
        )


def _bibtex_gaps(
    references: Sequence[Mapping[str, Any]],
    *,
    source: ContributionSource,
) -> list[ReportingGap]:
    """Expose citations that cannot be safely written to BibTeX without guessing."""
    gaps: list[ReportingGap] = []
    for reference in references:
        raw_text = reference.get("raw_text")
        if isinstance(raw_text, str) and raw_text.lstrip().startswith("@"):
            continue
        key = str(reference["key"])
        gaps.append(
            ReportingGap(
                gap_id=f"experiments:missing-bibtex:{key}",
                section=PaperSection.BACKGROUND,
                message=(
                    f"Citation {key!r} has no curated BibTeX record and was omitted from "
                    "references.bib."
                ),
                source=source,
            )
        )
    return gaps


def _render_references_bib(references: Sequence[Mapping[str, Any]]) -> str:
    """Render only curated BibTeX payloads; never synthesize bibliographic fields."""
    entries = [
        _align_bibtex_key(str(reference["raw_text"]).strip(), key=str(reference["key"]))
        for reference in references
        if isinstance(reference.get("raw_text"), str)
        and str(reference["raw_text"]).lstrip().startswith("@")
    ]
    return "" if not entries else "\n\n".join(entries) + "\n"


_BIBTEX_KEY = re.compile(r"^(\s*@[A-Za-z]+\s*\{\s*)[^,\s]+(\s*,)")


def _align_bibtex_key(raw_text: str, *, key: str) -> str:
    """Align a curated BibTeX entry identifier with its stable citation key."""
    match = _BIBTEX_KEY.match(raw_text)
    if match is None:
        return raw_text
    return f"{match.group(1)}{key}{match.group(2)}{raw_text[match.end() :]}"


def _normalize_reference(reference: Any) -> dict[str, Any]:
    """Normalize a Problems-compatible Citation object or JSON mapping."""
    jsonable = to_jsonable(reference)
    if not isinstance(jsonable, Mapping):
        raise ValidationError("Citation records must be JSON objects or dataclass instances.")
    normalized = {str(key): value for key, value in jsonable.items()}
    normalized["key"] = _required_text(normalized, "key", context="citation")
    normalized["title"] = _required_text(normalized, "title", context="citation")
    authors = normalized.get("authors")
    if authors is not None:
        normalized["authors"] = list(_string_tuple(authors, field_name="citation authors"))
    return normalized


def _reference_sequence(value: Any) -> tuple[Any, ...]:
    """Require a non-string sequence of citation records."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError("Paper contribution packet references must be a JSON array.")
    return tuple(value)


def _mapping_sequence(value: Any, field_name: str) -> tuple[Mapping[str, Any], ...]:
    """Require a sequence containing only JSON objects."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError(f"Paper contribution packet {field_name} must be a JSON array.")
    if not all(isinstance(item, Mapping) for item in value):
        raise ValidationError(f"Paper contribution packet {field_name} entries must be objects.")
    return cast(tuple[Mapping[str, Any], ...], tuple(value))


def _string_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    """Normalize a non-string sequence into unique, non-empty strings."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError(f"{field_name} must be a JSON array of strings.")
    normalized = tuple(str(item).strip() for item in value)
    if any(not item for item in normalized):
        raise ValidationError(f"{field_name} cannot contain empty values.")
    return tuple(dict.fromkeys(normalized))


def _mapping(value: Any, *, field_name: str) -> Mapping[str, Any]:
    """Require a JSON-compatible mapping."""
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a JSON object.")
    return {str(key): item for key, item in value.items()}


def _required_text(payload: Mapping[str, Any], key: str, *, context: str) -> str:
    """Return one required non-empty text field."""
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{context} {key} must be a non-empty string.")
    return value.strip()


def _coerce_enum(enum_type: type[StrEnum], value: Any, *, field_name: str) -> Any:
    """Coerce one string into a supported contract enum."""
    try:
        return enum_type(str(value))
    except ValueError as exc:
        supported = ", ".join(member.value for member in enum_type)
        raise ValidationError(f"{field_name} must be one of: {supported}.") from exc


def _experiments_source(study_id: str) -> ContributionSource:
    """Return provenance for contributions derived by this package."""
    try:
        package_version = version("design-research-experiments")
    except PackageNotFoundError:  # pragma: no cover - installed in normal use and tests.
        package_version = "0+unknown"
    return ContributionSource(
        package="design-research-experiments",
        package_version=package_version,
        component_type="study",
        component_id=study_id,
    )


_SECTION_ORDER = {section: index for index, section in enumerate(PaperSection)}


def _contribution_sort_key(contribution: PaperContribution) -> tuple[int, str]:
    """Return deterministic manuscript-section order for contributions."""
    raw_outline_order = contribution.metadata.get("outline_order", 100)
    outline_order = raw_outline_order if isinstance(raw_outline_order, int) else 100
    return (
        _SECTION_ORDER[contribution.section] * 1000 + outline_order,
        contribution.contribution_id,
    )


def _gap_sort_key(gap: ReportingGap) -> tuple[int, str]:
    """Return deterministic manuscript-section order for reporting gaps."""
    return (_SECTION_ORDER[gap.section], gap.gap_id)


def _count_phrase(count: int, singular: str) -> str:
    """Render a count with simple English pluralization."""
    suffix = "" if count == 1 else "s"
    return f"{count} {singular}{suffix}"
