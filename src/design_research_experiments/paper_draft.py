"""Explicit assembly of evidence-bounded, author-review paper drafts."""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from ._paper_draft_render import AUTHOR_REVIEW_LABEL, render_draft_files
from .paper import (
    PAPER_DRAFT_CONTRACT_VERSION,
    ContributionKind,
    PaperContributionPacket,
    PaperSupport,
    ReportingGap,
    collect_paper_support,
)
from .schemas import SCHEMA_VERSION, ValidationError, stable_json_dumps
from .study import Study

PAPER_DRAFT_VERSION = "0.1.0"
PAPER_DRAFT_DOCUMENT_STATUS = "paper-draft"
_PERSISTED_PACKET_FILE = "component_metadata.json"


class PaperDraftIncompleteError(ValidationError):
    """Raised after export when strict completeness finds evidence-critical TODOs."""

    def __init__(self, message: str, *, paths: Mapping[str, Path]) -> None:
        """Retain written paths so CLI callers can report the partial draft."""
        super().__init__(message)
        self.paths = dict(paths)


def export_paper_draft(
    study_or_output: Study | str | Path,
    *,
    output_dir: str | Path | None = None,
    component_packets: Sequence[PaperContributionPacket | Mapping[str, Any]] = (),
    user_references: Sequence[Any] = (),
    overwrite: bool = False,
    require_complete: bool = False,
) -> dict[str, Path]:
    """Explicitly assemble a review-required Markdown and compilable LaTeX draft.

    The source may be a live study, a serialized study, a completed artifact
    directory, or that directory's ``manifest.json``. By default output is
    written to ``paper-draft`` beneath the resolved artifact root.
    """
    study, artifact_root = _resolve_study_and_root(study_or_output)
    target = Path(output_dir) if output_dir is not None else artifact_root / "paper-draft"
    _validate_target(target, artifact_root=artifact_root)
    if target.exists() and any(target.iterdir()) and not overwrite:
        raise ValidationError(
            f"Paper-draft directory already contains files: {target}. Pass overwrite=True."
        )

    persisted_packets = _load_persisted_packets(artifact_root / _PERSISTED_PACKET_FILE)
    support = collect_paper_support(
        study,
        output_dir=artifact_root,
        component_packets=(*persisted_packets, *component_packets),
        user_references=user_references,
    )
    asset_paths, asset_gaps = _collect_assets(support, artifact_root=artifact_root)
    if asset_gaps:
        support = replace(
            support,
            reporting_gaps=tuple(
                sorted(
                    (*support.reporting_gaps, *asset_gaps),
                    key=lambda gap: (gap.section.value, gap.gap_id),
                )
            ),
        )

    stage = Path(tempfile.mkdtemp(prefix=".paper-draft-", dir=target.parent))
    try:
        paths = _write_draft(
            stage,
            study=study,
            support=support,
            artifact_root=artifact_root,
            asset_paths=asset_paths,
        )
        _install_stage(stage, target=target, overwrite=overwrite)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise

    installed_paths = {name: target / path.relative_to(stage) for name, path in paths.items()}
    if require_complete and support.reporting_gaps:
        raise PaperDraftIncompleteError(
            "Paper draft was written but contains evidence-critical TODOs.",
            paths=installed_paths,
        )
    return installed_paths


def _resolve_study_and_root(study_or_output: Study | str | Path) -> tuple[Study, Path]:
    """Resolve the study and artifact root from every supported source form."""
    if isinstance(study_or_output, Study):
        root = Path(study_or_output.output_dir or Path("artifacts") / study_or_output.study_id)
        return study_or_output, root
    source = Path(study_or_output)
    if source.is_dir():
        return Study.from_yaml(source / "study.yaml"), source
    if source.name == "manifest.json":
        return Study.from_yaml(source.parent / "study.yaml"), source.parent
    if source.suffix.lower() == ".json":
        return Study.from_json(source), source.parent
    return Study.from_yaml(source), source.parent


def _validate_target(target: Path, *, artifact_root: Path) -> None:
    """Reject unsafe targets before staging or replacement begins."""
    target.parent.mkdir(parents=True, exist_ok=True)
    resolved_target = target.resolve()
    resolved_root = artifact_root.resolve()
    if resolved_target == resolved_root or resolved_target in resolved_root.parents:
        raise ValidationError("Paper-draft output cannot replace the study artifact root.")
    if target.exists() and not target.is_dir():
        raise ValidationError(f"Paper-draft output exists and is not a directory: {target}.")
    if target.is_symlink():
        raise ValidationError(f"Paper-draft output cannot be a symlink: {target}.")


def _load_persisted_packets(path: Path) -> tuple[Mapping[str, Any], ...]:
    """Load optional portable sibling contribution packets from disk."""
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, Mapping) and "packets" in payload:
        payload = payload["packets"]
    if isinstance(payload, Mapping):
        return (cast(Mapping[str, Any], payload),)
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        if not all(isinstance(item, Mapping) for item in payload):
            raise ValidationError(f"{path} must contain only paper contribution packet objects.")
        return cast(tuple[Mapping[str, Any], ...], tuple(payload))
    raise ValidationError(f"{path} must contain a packet, packet array, or packets object.")


def _collect_assets(
    support: PaperSupport,
    *,
    artifact_root: Path,
) -> tuple[dict[str, tuple[Path, Path]], list[ReportingGap]]:
    """Resolve retained assets and convert missing render inputs into gaps."""
    assets: dict[str, tuple[Path, Path]] = {}
    gaps: list[ReportingGap] = []
    destinations: set[Path] = set()
    for contribution in support.contributions:
        if contribution.kind not in {ContributionKind.FIGURE, ContributionKind.TABLE}:
            continue
        raw_path = contribution.metadata.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            gaps.append(_asset_gap(contribution, "does not declare metadata.path"))
            continue
        source = _resolve_asset_path(artifact_root, raw_path)
        if not source.is_file():
            gaps.append(_asset_gap(contribution, f"references missing artifact {raw_path!r}"))
            continue
        folder = "figures" if contribution.kind == ContributionKind.FIGURE else "tables"
        filename = f"{_safe_name(contribution.contribution_id)}{source.suffix.lower()}"
        destination = Path(folder) / filename
        if destination in destinations:
            raise ValidationError(
                f"Paper contribution artifact destination collision: {destination}."
            )
        destinations.add(destination)
        assets[contribution.contribution_id] = (source, destination)
        if contribution.kind == ContributionKind.TABLE and source.suffix.lower() != ".tex":
            suffix = source.suffix or "an extensionless"
            gaps.append(
                _asset_gap(
                    contribution,
                    f"uses {suffix} table format that cannot be embedded in LaTeX",
                )
            )
    return assets, gaps


def _resolve_asset_path(artifact_root: Path, raw_path: str) -> Path:
    """Resolve one artifact path without allowing escape or symlink traversal."""
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValidationError(
            f"Paper contribution artifact path must be relative and safe: {raw_path!r}."
        )
    unresolved = artifact_root / relative
    current = artifact_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValidationError(
                f"Paper contribution artifact path cannot traverse a symlink: {raw_path!r}."
            )
    resolved_root = artifact_root.resolve()
    resolved = unresolved.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValidationError(
            f"Paper contribution artifact escapes the artifact root: {raw_path!r}."
        )
    return resolved


def _asset_gap(contribution: Any, reason: str) -> ReportingGap:
    """Build one evidence-critical reporting gap for an unusable asset."""
    return ReportingGap(
        gap_id=f"experiments:missing-asset:{contribution.contribution_id}",
        section=contribution.section,
        message=f"Contribution {contribution.contribution_id!r} {reason}.",
        source=contribution.source,
        evidence_refs=contribution.evidence_refs,
    )


def _safe_name(value: str) -> str:
    """Convert a stable contribution ID into a portable asset filename."""
    normalized = "".join(character if character.isalnum() else "-" for character in value)
    return normalized.strip("-") or "artifact"


def _write_draft(
    stage: Path,
    *,
    study: Study,
    support: PaperSupport,
    artifact_root: Path,
    asset_paths: Mapping[str, tuple[Path, Path]],
) -> dict[str, Path]:
    """Write generated text, copied assets, and manifest into a staging tree."""
    relative_assets = {key: destination for key, (_, destination) in asset_paths.items()}
    files = render_draft_files(study, support, asset_paths=relative_assets)
    paths: dict[str, Path] = {}
    for relative, content in files.items():
        path = stage / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        paths[relative.as_posix()] = path
    for folder in (stage / "tables", stage / "figures"):
        folder.mkdir(parents=True, exist_ok=True)
    for contribution_id, (source, destination) in asset_paths.items():
        destination_path = stage / destination
        shutil.copy2(source, destination_path)
        paths[f"asset:{contribution_id}"] = destination_path

    manifest_path = stage / "paper_draft_manifest.json"
    manifest_path.write_text(
        stable_json_dumps(
            _draft_manifest(
                study,
                support,
                artifact_root=artifact_root,
                asset_paths=relative_assets,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    paths[manifest_path.name] = manifest_path
    return paths


def _draft_manifest(
    study: Study,
    support: PaperSupport,
    *,
    artifact_root: Path,
    asset_paths: Mapping[str, Path],
) -> dict[str, Any]:
    """Build the auditable paper-draft manifest."""
    manifest_path = artifact_root / "manifest.json"
    source_schema = SCHEMA_VERSION
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(payload, Mapping):
            source_schema = str(payload.get("schema_version", SCHEMA_VERSION))
    return {
        "paper_draft_version": PAPER_DRAFT_VERSION,
        "paper_contribution_schema_version": PAPER_DRAFT_CONTRACT_VERSION,
        "document_status": PAPER_DRAFT_DOCUMENT_STATUS,
        "document_label": AUTHOR_REVIEW_LABEL,
        "author_review_required": True,
        "study_id": study.study_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_artifact_schema_version": source_schema,
        "completeness": "partial" if support.reporting_gaps else "full",
        "run_accounting": dict(support.run_accounting),
        "evidence_backed_blocks": len(support.contributions),
        "partial_blocks": len(support.reporting_gaps),
        "todo_blocks": len(support.reporting_gaps) + _author_todo_count(study, support),
        "citation_count": len(support.references),
        "figures": sorted(
            path.as_posix() for path in asset_paths.values() if path.parts[0] == "figures"
        ),
        "tables": sorted(
            path.as_posix() for path in asset_paths.values() if path.parts[0] == "tables"
        ),
        "contributions": [
            {
                "contribution_id": item.contribution_id,
                "section": item.section.value,
                "kind": item.kind.value,
                "evidence_basis": item.evidence_basis.value,
                "source": item.source.to_dict(),
                "evidence_refs": list(item.evidence_refs),
            }
            for item in support.contributions
        ],
        "reporting_gaps": [gap.to_dict() for gap in support.reporting_gaps],
    }


def _install_stage(stage: Path, *, target: Path, overwrite: bool) -> None:
    """Install a completed staging tree with rollback-safe replacement."""
    backup: Path | None = None
    if target.exists():
        if any(target.iterdir()) and not overwrite:
            raise ValidationError(
                f"Paper-draft directory already contains files: {target}. Pass overwrite=True."
            )
        if any(target.iterdir()):
            backup = Path(tempfile.mkdtemp(prefix=f".{target.name}-backup-", dir=target.parent))
            backup.rmdir()
            target.rename(backup)
        else:
            target.rmdir()
    try:
        stage.rename(target)
    except Exception:
        if backup is not None and backup.exists() and not target.exists():
            backup.rename(target)
        raise
    if backup is not None:
        shutil.rmtree(backup)


def _author_todo_count(study: Study, support: PaperSupport) -> int:
    """Count generated author-judgment TODOs without treating them as evidence gaps."""
    count = 7
    if not any(item.section.value == "background" for item in support.contributions):
        count += 1
    for hypothesis in study.hypotheses:
        count += 1
        linked = any(
            hypothesis.hypothesis_id in _metadata_strings(item.metadata.get("hypothesis_ids"))
            and item.evidence_basis.value in {"observed", "analyzed"}
            for item in support.contributions
        )
        if not linked:
            count += 1
    return count


def _metadata_strings(value: Any) -> tuple[str, ...]:
    """Normalize a metadata array to strings without accepting scalar text."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)
