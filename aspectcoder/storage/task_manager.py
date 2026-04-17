from __future__ import annotations
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from aspectcoder.models.plan import Plan
from aspectcoder.models.verdict import PlanVerdict, ReviewVerdict
from aspectcoder.models.code import GenerationResult
from aspectcoder.models.job import JobState, JobStatus, VerdictRecord
from aspectcoder.storage.snapshot import (
    write_plan,
    write_plan_verdict,
    write_code,
    write_verdicts,
    write_state,
    read_plan,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


class TaskManager:
    def __init__(self, jobs_dir: Path = Path(".aspectcoder/jobs")):
        self.jobs_dir = Path(jobs_dir)

    def _job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def _version_dir(self, job_id: str, version: int) -> Path:
        return self._job_dir(job_id) / f"v{version}"

    def _save(self, state: JobState) -> JobState:
        updated = state.model_copy(update={"updated_at": _now()})
        write_state(self._job_dir(updated.job_id), updated)
        return updated

    # ── public API ────────────────────────────────────────────────────────────

    def get_job(self, job_id: str) -> JobState:
        job_dir = self._job_dir(job_id)
        state_file = job_dir / "state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"No job found with id '{job_id}'")
        from aspectcoder.storage.snapshot import read_state
        return read_state(job_dir)

    def create_job(self, task_description: str) -> JobState:
        now = _now()
        state = JobState(
            job_id=_short_id(),
            task_description=task_description,
            status=JobStatus.RUNNING,
            current_version=0,
            created_at=now,
            updated_at=now,
        )
        return self._save(state)

    def snapshot_plan(
        self, state: JobState, plan: Plan, *, verdict: PlanVerdict | None = None
    ) -> JobState:
        new_version = state.current_version + 1
        version_dir = self._version_dir(state.job_id, new_version)
        write_plan(version_dir, plan)
        if verdict is not None:
            write_plan_verdict(version_dir, verdict)
        return self._save(state.model_copy(update={"current_version": new_version}))

    def snapshot_code(self, state: JobState, generated: GenerationResult) -> JobState:
        new_version = state.current_version + 1
        version_dir = self._version_dir(state.job_id, new_version)

        # copy current plan into this version for reference
        prev_version_dir = self._version_dir(state.job_id, state.current_version)
        if (prev_version_dir / "plan.json").exists():
            plan = read_plan(prev_version_dir)
            write_plan(version_dir, plan)

        write_code(version_dir, generated)
        return self._save(state.model_copy(update={"current_version": new_version}))

    def snapshot_attempt(
        self, state: JobState, generated: GenerationResult, verdicts: list[ReviewVerdict]
    ) -> JobState:
        new_version = state.current_version + 1
        version_dir = self._version_dir(state.job_id, new_version)

        prev_version_dir = self._version_dir(state.job_id, state.current_version)
        if (prev_version_dir / "plan.json").exists():
            plan = read_plan(prev_version_dir)
            write_plan(version_dir, plan)

        write_code(version_dir, generated)
        write_verdicts(version_dir, verdicts)

        records = [
            VerdictRecord(
                version=new_version,
                reviewer=v.reviewer.value,
                pass_=v.pass_,
                issues=[issue.description for issue in v.issues],
            )
            for v in verdicts
        ]
        updated_verdicts = list(state.verdicts) + records
        return self._save(state.model_copy(update={
            "current_version": new_version,
            "verdicts": updated_verdicts,
        }))

    def add_verdict(self, state: JobState, verdict: ReviewVerdict) -> JobState:
        record = VerdictRecord(
            version=state.current_version,
            reviewer=verdict.reviewer.value,
            pass_=verdict.pass_,
            issues=[issue.description for issue in verdict.issues],
        )
        updated_verdicts = list(state.verdicts) + [record]
        return self._save(state.model_copy(update={"verdicts": updated_verdicts}))

    def complete_job(self, state: JobState) -> JobState:
        return self._save(state.model_copy(update={"status": JobStatus.DONE}))

    def fail_job(self, state: JobState) -> JobState:
        return self._save(state.model_copy(update={"status": JobStatus.FAILED}))

    def rollback(self, job_id: str, version: int, project_root: Path) -> list[str]:
        job_dir = self._job_dir(job_id)
        code_dir = self._version_dir(job_id, version) / "code"
        backup_dir = job_dir / "pre-rollback"
        restored: list[str] = []

        for src in code_dir.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(code_dir)
            dest = project_root / rel
            if dest.exists():
                backup = backup_dir / rel
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, backup)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            restored.append(str(rel))

        return restored
