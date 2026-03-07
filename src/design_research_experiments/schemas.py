"""Shared schema primitives and serialization helpers for experiment workflows."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import platform
import socket
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any, cast

SCHEMA_VERSION = "0.1.0"


class ValidationError(ValueError):
    """Raised when a schema object fails validation."""


class ConstraintSeverity(StrEnum):
    """Severity level for admissibility constraints."""

    ERROR = "error"
    WARNING = "warning"


class RunStatus(StrEnum):
    """Lifecycle status of one run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ObservationLevel(StrEnum):
    """Granularity level for an observation row."""

    STUDY = "study"
    RUN = "run"
    TRIAL = "trial"
    STEP = "step"
    TOOL_CALL = "tool-call"
    EVALUATION = "evaluation"


@dataclass(slots=True)
class SeedPolicy:
    """Deterministic seed policy for run generation.

    Args:
        base_seed: Study-wide base seed.
        strategy: Seed derivation strategy name.
        per_run_offset: Numeric offset mixed into each run seed.
    """

    base_seed: int = 0
    strategy: str = "condition_replicate"
    per_run_offset: int = 9973

    def derive_seed(self, study_id: str, condition_id: str, replicate: int, salt: str = "") -> int:
        """Derive one deterministic per-run seed."""
        payload = {
            "base_seed": self.base_seed,
            "strategy": self.strategy,
            "per_run_offset": self.per_run_offset,
            "study_id": study_id,
            "condition_id": condition_id,
            "replicate": replicate,
            "salt": salt,
        }
        digest = hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()
        return int(digest[:16], 16) % (2**31 - 1)


@dataclass(slots=True)
class RunBudget:
    """Execution budget controls for one study.

    Args:
        replicates: Number of run replicates for each unit.
        max_runs: Optional upper bound on total runs.
        parallelism: Local worker count.
        fail_fast: Stop after first failure when `True`.
    """

    replicates: int = 1
    max_runs: int | None = None
    parallelism: int = 1
    fail_fast: bool = False

    def __post_init__(self) -> None:
        """Validate budget shape."""
        if self.replicates < 1:
            raise ValidationError("RunBudget.replicates must be >= 1.")
        if self.parallelism < 1:
            raise ValidationError("RunBudget.parallelism must be >= 1.")
        if self.max_runs is not None and self.max_runs < 1:
            raise ValidationError("RunBudget.max_runs must be >= 1 when provided.")


@dataclass(slots=True)
class ProvenanceMetadata:
    """Captured runtime provenance for reproducibility.

    Args:
        captured_at: UTC timestamp when provenance was captured.
        host: Hostname where execution happened.
        platform: Platform descriptor.
        python_version: Runtime Python version.
        package_versions: Resolved package versions.
        git_sha: Git commit SHA when available.
        extra: Additional caller-provided metadata.
    """

    captured_at: str
    host: str
    platform: str
    python_version: str
    package_versions: dict[str, str] = field(default_factory=dict)
    git_sha: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def capture(
        cls,
        package_names: Iterable[str] = (),
        *,
        cwd: Path | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> ProvenanceMetadata:
        """Capture reproducibility metadata from the local environment."""
        versions: dict[str, str] = {}
        for package_name in package_names:
            try:
                versions[package_name] = importlib.metadata.version(package_name)
            except importlib.metadata.PackageNotFoundError:
                versions[package_name] = "not-installed"

        return cls(
            captured_at=utc_now_iso(),
            host=socket.gethostname(),
            platform=platform.platform(),
            python_version=sys.version.split()[0],
            package_versions=versions,
            git_sha=resolve_git_sha(cwd=cwd),
            extra=dict(extra or {}),
        )


@dataclass(slots=True)
class Observation:
    """Normalized process trace observation.

    Args:
        timestamp: UTC timestamp string.
        record_id: Stable row identifier.
        text: Optional human-readable event text.
        session_id: Session or conversation identifier.
        actor_id: Actor identifier.
        event_type: Event kind label.
        meta_json: Structured event metadata.
        level: Observation granularity.
        study_id: Optional study ID.
        run_id: Optional run ID.
        condition_id: Optional condition ID.
        trial_id: Optional trial ID.
        step_id: Optional step ID.
        tool_name: Optional tool name.
        evaluation_id: Optional evaluation record ID.
    """

    timestamp: str
    record_id: str
    text: str
    session_id: str
    actor_id: str
    event_type: str
    meta_json: dict[str, Any] = field(default_factory=dict)
    level: ObservationLevel = ObservationLevel.STEP
    study_id: str | None = None
    run_id: str | None = None
    condition_id: str | None = None
    trial_id: str | None = None
    step_id: str | None = None
    tool_name: str | None = None
    evaluation_id: str | None = None

    def to_row(self) -> dict[str, Any]:
        """Convert the observation to one export row."""
        return {
            "timestamp": self.timestamp,
            "record_id": self.record_id,
            "text": self.text,
            "session_id": self.session_id,
            "actor_id": self.actor_id,
            "event_type": self.event_type,
            "meta_json": stable_json_dumps(self.meta_json),
            "level": self.level.value,
            "study_id": self.study_id,
            "run_id": self.run_id,
            "condition_id": self.condition_id,
            "trial_id": self.trial_id,
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "evaluation_id": self.evaluation_id,
        }


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp without microseconds."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def resolve_git_sha(cwd: Path | None = None) -> str | None:
    """Resolve the current git SHA if the working directory is a git checkout."""
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd) if cwd is not None else None,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return output or None


def stable_json_dumps(data: Any) -> str:
    """Serialize arbitrary data deterministically for IDs and manifests."""
    return json.dumps(to_jsonable(data), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def to_jsonable(value: Any) -> Any:
    """Recursively convert a Python value to a JSON-serializable structure."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_jsonable(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))
    return str(value)


def hash_identifier(prefix: str, payload: Mapping[str, Any], *, length: int = 12) -> str:
    """Build a deterministic short identifier from a stable payload hash."""
    digest = hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:length]}"


def load_callable(reference: str) -> Callable[..., Any]:
    """Load a callable from a `module:attribute` reference string."""
    if ":" not in reference:
        raise ValidationError(
            "Callable reference must use the format 'module.submodule:callable_name'."
        )

    module_name, attribute_name = reference.split(":", maxsplit=1)
    module = importlib.import_module(module_name)
    loaded = getattr(module, attribute_name)
    if not callable(loaded):
        raise ValidationError(f"Reference '{reference}' does not resolve to a callable.")
    return cast(Callable[..., Any], loaded)
