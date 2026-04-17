from __future__ import annotations
import json
from pathlib import Path

from aspectcoder.models.plan import Plan
from aspectcoder.models.verdict import PlanVerdict
from aspectcoder.models.code import GenerationResult
from aspectcoder.models.job import JobState


def write_plan(version_dir: Path, plan: Plan) -> None:
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "plan.json").write_text(plan.model_dump_json(indent=2))


def write_plan_verdict(version_dir: Path, verdict: PlanVerdict) -> None:
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "plan_verdict.json").write_text(verdict.model_dump_json(indent=2))


def write_code(version_dir: Path, generated: GenerationResult) -> None:
    code_dir = version_dir / "code"
    for subtask in generated.subtasks:
        dest = code_dir / subtask.file_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(subtask.code)


def write_output_files(generated: GenerationResult, project_root: Path) -> list[str]:
    """Write generated files into the project directory. Returns list of relative paths written."""
    written: list[str] = []
    for subtask in generated.subtasks:
        dest = project_root / subtask.file_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(subtask.code)
        written.append(subtask.file_path)
    return written


def write_state(job_dir: Path, state: JobState) -> None:
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "state.json").write_text(state.model_dump_json(indent=2))


def read_state(job_dir: Path) -> JobState:
    data = json.loads((job_dir / "state.json").read_text())
    return JobState.model_validate(data)


def read_plan(version_dir: Path) -> Plan:
    data = json.loads((version_dir / "plan.json").read_text())
    return Plan.model_validate(data)
