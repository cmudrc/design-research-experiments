"""Run orchestration engines and reproducible execution helpers."""

from __future__ import annotations

import importlib
import random
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tqdm.auto import tqdm

from .adapters.agents import execute_agent
from .adapters.problems import evaluate_problem, resolve_problem
from .artifacts import (
    checkpoint_run_result,
    export_canonical_artifacts,
    load_checkpointed_run_results,
)
from .conditions import Condition
from .designs import build_design
from .metrics import compose_metrics
from .schemas import RunStatus, ValidationError, hash_identifier, stable_json_dumps, utc_now_iso
from .study import RunResult, RunSpec, Study, validate_study


@dataclass(slots=True)
class DryRunReport:
    """Dry-run validation report for a planned execution."""

    errors: list[str]
    planned_runs: int


class _NoOpProgressBar:
    """Progress-bar shim used when visual progress is disabled."""

    def update(self, _steps: int = 1) -> None:
        """Ignore progress updates."""

    def set_postfix(
        self,
        _ordered_dict: Mapping[str, int] | None = None,
        *,
        refresh: bool = True,
    ) -> None:
        """Ignore postfix updates."""
        del refresh

    def close(self) -> None:
        """Ignore close calls."""


@dataclass(slots=True)
class _RunProgress:
    """Centralized progress adapter for run execution."""

    total: int
    initial: int
    success: int
    failed: int
    _bar: Any

    def __post_init__(self) -> None:
        """Synchronize initial success and failure counts."""
        self._sync_postfix()

    def record_result(self, result: RunResult) -> None:
        """Advance progress after one completed run."""
        if result.status == RunStatus.SUCCESS:
            self.success += 1
        elif result.status == RunStatus.FAILED:
            self.failed += 1
        self._bar.update(1)
        self._sync_postfix()

    def close(self) -> None:
        """Close the underlying progress bar."""
        self._bar.close()

    def _sync_postfix(self) -> None:
        """Refresh success and failure counters."""
        self._bar.set_postfix({"success": self.success, "failed": self.failed})


class SerialRunner:
    """Serial orchestration runner."""

    def run(
        self,
        *,
        run_specs: Sequence[RunSpec],
        condition_by_id: Mapping[str, Condition],
        agent_factories: Mapping[str, Callable[[Condition], Any]] | None,
        problem_registry: Mapping[str, Any] | None,
        output_dir: Path,
        checkpoint: bool,
        fail_fast: bool,
        progress: _RunProgress,
    ) -> list[RunResult]:
        """Execute all run specs one-by-one."""
        results: list[RunResult] = []
        for run_spec in run_specs:
            condition = condition_by_id[run_spec.condition_id]
            result = _execute_single_run(
                run_spec=run_spec,
                condition=condition,
                agent_factories=agent_factories,
                problem_registry=problem_registry,
            )
            results.append(result)
            if checkpoint:
                checkpoint_run_result(result, output_dir=output_dir)
            progress.record_result(result)
            if fail_fast and result.status == RunStatus.FAILED:
                break
        return results


class LocalParallelRunner:
    """Thread-based local parallel orchestration runner."""

    def run(
        self,
        *,
        run_specs: Sequence[RunSpec],
        condition_by_id: Mapping[str, Condition],
        agent_factories: Mapping[str, Callable[[Condition], Any]] | None,
        problem_registry: Mapping[str, Any] | None,
        output_dir: Path,
        checkpoint: bool,
        fail_fast: bool,
        max_workers: int,
        progress: _RunProgress,
    ) -> list[RunResult]:
        """Execute run specs in a local thread pool."""
        results: list[RunResult] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_by_run_id: dict[Future[RunResult], str] = {}
            for run_spec in run_specs:
                condition = condition_by_id[run_spec.condition_id]
                future = executor.submit(
                    _execute_single_run,
                    run_spec=run_spec,
                    condition=condition,
                    agent_factories=agent_factories,
                    problem_registry=problem_registry,
                )
                future_by_run_id[future] = run_spec.run_id

            for future in as_completed(future_by_run_id):
                result = future.result()
                results.append(result)
                if checkpoint:
                    checkpoint_run_result(result, output_dir=output_dir)
                progress.record_result(result)
                if fail_fast and result.status == RunStatus.FAILED:
                    for pending_future in future_by_run_id:
                        if pending_future.done():
                            continue
                        pending_future.cancel()
                    break

        return results


def run_study(
    study: Study,
    *,
    conditions: Sequence[Condition] | None = None,
    agent_factories: Mapping[str, Callable[[Condition], Any]] | None = None,
    problem_registry: Mapping[str, Any] | None = None,
    parallelism: int | None = None,
    dry_run: bool = False,
    resume: bool = False,
    checkpoint: bool = True,
    include_sqlite: bool = False,
    show_progress: bool | None = None,
) -> list[RunResult]:
    """Run a study end-to-end and export canonical artifacts."""
    resolved_conditions = list(conditions) if conditions is not None else build_design(study)
    report = dry_run_validate(study, conditions=resolved_conditions)
    if report.errors:
        raise ValidationError("\n".join(report.errors))
    if dry_run:
        return []

    output_dir = Path(study.output_dir or Path("artifacts") / study.study_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_run_specs = _build_run_specs(study=study, conditions=resolved_conditions)
    planned_run_ids = {run_spec.run_id for run_spec in all_run_specs}
    condition_by_id = {condition.condition_id: condition for condition in resolved_conditions}

    existing_results: list[RunResult] = []
    completed_run_ids: set[str] = set()
    if resume:
        checkpointed = load_checkpointed_run_results(output_dir)
        existing_results = list(checkpointed.values())
        completed_run_ids = set(checkpointed)

    pending_run_specs = [
        run_spec for run_spec in all_run_specs if run_spec.run_id not in completed_run_ids
    ]
    existing_progress_results = [
        result for result in existing_results if result.run_id in planned_run_ids
    ]

    resolved_parallelism = parallelism if parallelism is not None else study.run_budget.parallelism
    if resolved_parallelism < 1:
        raise ValidationError("parallelism must be >= 1.")
    progress = _create_run_progress(
        study_id=study.study_id,
        total=len(all_run_specs),
        initial=len(all_run_specs) - len(pending_run_specs),
        run_results=existing_progress_results,
        pending_runs=len(pending_run_specs),
        show_progress=show_progress,
    )
    try:
        if resolved_parallelism == 1:
            serial_runner = SerialRunner()
            new_results = serial_runner.run(
                run_specs=pending_run_specs,
                condition_by_id=condition_by_id,
                agent_factories=agent_factories,
                problem_registry=problem_registry,
                output_dir=output_dir,
                checkpoint=checkpoint,
                fail_fast=study.run_budget.fail_fast,
                progress=progress,
            )
        else:
            parallel_runner = LocalParallelRunner()
            new_results = parallel_runner.run(
                run_specs=pending_run_specs,
                condition_by_id=condition_by_id,
                agent_factories=agent_factories,
                problem_registry=problem_registry,
                output_dir=output_dir,
                checkpoint=checkpoint,
                fail_fast=study.run_budget.fail_fast,
                max_workers=resolved_parallelism,
                progress=progress,
            )

        all_results = existing_results + new_results
        export_canonical_artifacts(
            study=study,
            conditions=resolved_conditions,
            run_results=all_results,
            output_dir=output_dir,
            include_sqlite=include_sqlite,
        )
        return all_results
    finally:
        progress.close()


def resume_study(
    study: Study,
    *,
    conditions: Sequence[Condition] | None = None,
    agent_factories: Mapping[str, Callable[[Condition], Any]] | None = None,
    problem_registry: Mapping[str, Any] | None = None,
    parallelism: int | None = None,
    checkpoint: bool = True,
    include_sqlite: bool = False,
    show_progress: bool | None = None,
) -> list[RunResult]:
    """Resume a study from checkpointed run results."""
    return run_study(
        study,
        conditions=conditions,
        agent_factories=agent_factories,
        problem_registry=problem_registry,
        parallelism=parallelism,
        dry_run=False,
        resume=True,
        checkpoint=checkpoint,
        include_sqlite=include_sqlite,
        show_progress=show_progress,
    )


def dry_run_validate(study: Study, *, conditions: Sequence[Condition]) -> DryRunReport:
    """Validate run inputs before launching execution."""
    errors = list(validate_study(study))

    admissible_conditions = [condition for condition in conditions if condition.admissible]
    if not admissible_conditions:
        errors.append("No admissible conditions are available to execute.")

    planned_runs = len(_build_run_specs(study=study, conditions=conditions))
    if planned_runs < 1:
        errors.append("No run specifications were generated.")

    if study.run_budget.max_runs is not None and planned_runs > study.run_budget.max_runs:
        errors.append(
            "Planned runs "
            f"({planned_runs}) exceed run budget max_runs ({study.run_budget.max_runs})."
        )

    return DryRunReport(errors=errors, planned_runs=planned_runs)


def reproducible_seed(seed: int) -> Any:
    """Context manager preserving and restoring random RNG state."""
    return _reproducible_seed(seed)


@contextmanager
def _reproducible_seed(seed: int) -> Any:
    """Temporarily set deterministic RNG seeds for one run."""
    previous_state = random.getstate()
    random.seed(seed)

    numpy_state: tuple[Any, Any] | None = None
    try:
        numpy_module = importlib.import_module("numpy")
        numpy_random = numpy_module.random
        get_state = numpy_random.get_state
        set_state = numpy_random.set_state
        seed_function = numpy_random.seed

        numpy_state = (get_state(), set_state)
        seed_function(seed)
    except Exception:
        numpy_state = None

    try:
        yield
    finally:
        random.setstate(previous_state)
        if numpy_state is not None:
            state, set_state = numpy_state
            set_state(state)


def _build_run_specs(study: Study, conditions: Sequence[Condition]) -> list[RunSpec]:
    """Materialize deterministic run specs for all admissible conditions."""
    admissible_conditions = [condition for condition in conditions if condition.admissible]

    run_specs: list[RunSpec] = []
    for condition in admissible_conditions:
        agent_ids = _resolve_agent_ids(study=study, condition=condition)
        problem_ids = _resolve_problem_ids(study=study, condition=condition)

        for replicate in range(1, study.run_budget.replicates + 1):
            for agent_id in agent_ids:
                for problem_id in problem_ids:
                    run_id = hash_identifier(
                        "run",
                        {
                            "study_id": study.study_id,
                            "condition_id": condition.condition_id,
                            "replicate": replicate,
                            "agent_id": agent_id,
                            "problem_id": problem_id,
                        },
                    )
                    seed = study.seed_policy.derive_seed(
                        study_id=study.study_id,
                        condition_id=condition.condition_id,
                        replicate=replicate,
                        salt=f"{agent_id}:{problem_id}",
                    )
                    run_specs.append(
                        RunSpec(
                            run_id=run_id,
                            study_id=study.study_id,
                            condition_id=condition.condition_id,
                            problem_id=problem_id,
                            replicate=replicate,
                            seed=seed,
                            agent_spec_ref=agent_id,
                            problem_spec_ref=problem_id,
                            execution_metadata={
                                "agent_id": agent_id,
                                "problem_id": problem_id,
                                "condition_fingerprint": condition.metadata.get("fingerprint"),
                            },
                        )
                    )

    if study.run_budget.max_runs is not None:
        return run_specs[: study.run_budget.max_runs]
    return run_specs


def _resolve_agent_ids(study: Study, condition: Condition) -> tuple[str, ...]:
    """Resolve agent IDs for one condition."""
    for key in ("agent_id", "agent", "agent_spec"):
        if key in condition.factor_assignments:
            return (str(condition.factor_assignments[key]),)

    if study.agent_specs:
        return tuple(study.agent_specs)

    return ("default-agent",)


def _resolve_problem_ids(study: Study, condition: Condition) -> tuple[str, ...]:
    """Resolve problem IDs for one condition."""
    for key in ("problem_id", "problem"):
        if key in condition.factor_assignments:
            return (str(condition.factor_assignments[key]),)

    if study.problem_ids:
        return tuple(study.problem_ids)

    return ("default-problem",)


def _create_run_progress(
    *,
    study_id: str,
    total: int,
    initial: int,
    run_results: Sequence[RunResult],
    pending_runs: int,
    show_progress: bool | None,
) -> _RunProgress:
    """Build the run-progress adapter for one execution."""
    success = sum(1 for result in run_results if result.status == RunStatus.SUCCESS)
    failed = sum(1 for result in run_results if result.status == RunStatus.FAILED)

    if _should_render_progress(show_progress=show_progress, pending_runs=pending_runs):
        bar: Any = tqdm(
            total=total,
            initial=initial,
            desc=study_id,
            unit="run",
            dynamic_ncols=True,
            leave=True,
            file=sys.stderr,
        )
    else:
        bar = _NoOpProgressBar()

    return _RunProgress(total=total, initial=initial, success=success, failed=failed, _bar=bar)


def _should_render_progress(*, show_progress: bool | None, pending_runs: int) -> bool:
    """Decide whether to create a visible progress bar."""
    if pending_runs < 1:
        return False
    if show_progress is not None:
        return show_progress
    stderr = sys.stderr
    isatty = getattr(stderr, "isatty", None)
    return bool(callable(isatty) and isatty())


def _execute_single_run(
    *,
    run_spec: RunSpec,
    condition: Condition,
    agent_factories: Mapping[str, Callable[[Condition], Any]] | None,
    problem_registry: Mapping[str, Any] | None,
) -> RunResult:
    """Execute one run spec with failure isolation."""
    started_at = utc_now_iso()
    start_time = time.perf_counter()

    try:
        with reproducible_seed(run_spec.seed):
            problem_packet = resolve_problem(
                run_spec.problem_spec_ref,
                registry=problem_registry,
            )
            run_spec.execution_metadata["problem_family"] = problem_packet.family

            agent_execution = execute_agent(
                agent_spec_ref=run_spec.agent_spec_ref,
                run_spec=run_spec,
                condition=condition,
                problem_packet=problem_packet,
                factories=agent_factories,
            )

            evaluation_rows = evaluate_problem(problem_packet, agent_execution.output)
            for row in evaluation_rows:
                row["run_id"] = run_spec.run_id

            latency_s = time.perf_counter() - start_time
            cost_usd = float(agent_execution.metrics.get("cost_usd", 0.0) or 0.0)
            metrics = compose_metrics(
                agent_metrics=agent_execution.metrics,
                evaluation_rows=evaluation_rows,
                observations=agent_execution.events,
                latency_s=latency_s,
                cost_usd=cost_usd,
            )

            provenance_info = {
                "agent_id": run_spec.execution_metadata.get("agent_id"),
                "problem_id": run_spec.problem_id,
                "problem_family": problem_packet.family,
                "model_name": agent_execution.metadata.get("model_name"),
                "execution_metadata": stable_json_dumps(run_spec.execution_metadata),
            }

            return RunResult(
                run_id=run_spec.run_id,
                status=RunStatus.SUCCESS,
                outputs=agent_execution.output,
                metrics=metrics,
                evaluator_outputs=evaluation_rows,
                cost=cost_usd,
                latency=latency_s,
                trace_refs=list(agent_execution.trace_refs),
                artifact_refs=[],
                error_info=None,
                provenance_info=provenance_info,
                observations=list(agent_execution.events),
                run_spec=run_spec,
                started_at=started_at,
                ended_at=utc_now_iso(),
            )
    except Exception as exc:
        latency_s = time.perf_counter() - start_time
        return RunResult(
            run_id=run_spec.run_id,
            status=RunStatus.FAILED,
            outputs={},
            metrics={"latency_s": latency_s},
            evaluator_outputs=[],
            cost=0.0,
            latency=latency_s,
            trace_refs=[],
            artifact_refs=[],
            error_info=f"{type(exc).__name__}: {exc}",
            provenance_info={"agent_id": run_spec.execution_metadata.get("agent_id")},
            observations=[],
            run_spec=run_spec,
            started_at=started_at,
            ended_at=utc_now_iso(),
        )
