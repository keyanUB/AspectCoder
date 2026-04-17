import json
from datetime import datetime, timezone
from pathlib import Path
import pytest

from aspectcoder.storage.snapshot import (
    write_plan,
    write_plan_verdict,
    write_code,
    write_output_files,
    write_state,
    read_state,
    read_plan,
)
from aspectcoder.models.plan import Plan, Subtask
from aspectcoder.models.verdict import PlanVerdict
from aspectcoder.models.code import GenerationResult, GeneratedCode
from aspectcoder.models.job import JobState, JobStatus


@pytest.fixture
def sample_plan():
    return Plan(
        task_id="task-1",
        task_description="Add binary_search",
        approach="Iterative",
        subtasks=[
            Subtask(id="subtask-1", description="Implement", target_file="src/utils.c", language="c")
        ],
        target_files=["src/utils.c"],
        primary_language="c",
        confidence=0.9,
    )


@pytest.fixture
def sample_verdict():
    return PlanVerdict(pass_=True, confidence=0.95, issues=[])


@pytest.fixture
def sample_generation():
    return GenerationResult(
        subtasks=[
            GeneratedCode(
                subtask_id="subtask-1",
                language="c",
                file_path="src/utils.c",
                code="int binary_search(int *a, int n, int t) { return -1; }",
                explanation="Stub",
                confidence=0.85,
            )
        ]
    )


@pytest.fixture
def sample_state():
    now = datetime.now(timezone.utc)
    return JobState(
        job_id="abc123",
        task_description="Add binary_search",
        status=JobStatus.RUNNING,
        current_version=1,
        created_at=now,
        updated_at=now,
    )


# ── write_plan ────────────────────────────────────────────────────────────────

def test_write_plan_creates_plan_json(tmp_path, sample_plan):
    version_dir = tmp_path / "v1"
    write_plan(version_dir, sample_plan)
    plan_file = version_dir / "plan.json"
    assert plan_file.exists()
    data = json.loads(plan_file.read_text())
    assert data["task_id"] == "task-1"
    assert data["approach"] == "Iterative"


# ── write_plan_verdict ────────────────────────────────────────────────────────

def test_write_plan_verdict_creates_verdict_json(tmp_path, sample_verdict):
    version_dir = tmp_path / "v1"
    write_plan_verdict(version_dir, sample_verdict)
    verdict_file = version_dir / "plan_verdict.json"
    assert verdict_file.exists()
    data = json.loads(verdict_file.read_text())
    assert data["pass_"] is True


# ── write_code ────────────────────────────────────────────────────────────────

def test_write_code_creates_code_files(tmp_path, sample_generation):
    version_dir = tmp_path / "v1"
    write_code(version_dir, sample_generation)
    code_file = version_dir / "code" / "src" / "utils.c"
    assert code_file.exists()
    assert "binary_search" in code_file.read_text()


def test_write_code_preserves_nested_paths(tmp_path):
    gen = GenerationResult(
        subtasks=[
            GeneratedCode(
                subtask_id="s1",
                language="python",
                file_path="src/lib/helpers.py",
                code="def helper(): pass",
                explanation="",
                confidence=0.9,
            )
        ]
    )
    version_dir = tmp_path / "v1"
    write_code(version_dir, gen)
    assert (version_dir / "code" / "src" / "lib" / "helpers.py").exists()


# ── write_state / read_state ──────────────────────────────────────────────────

def test_write_and_read_state_round_trips(tmp_path, sample_state):
    write_state(tmp_path, sample_state)
    state_file = tmp_path / "state.json"
    assert state_file.exists()
    restored = read_state(tmp_path)
    assert restored.job_id == "abc123"
    assert restored.status == JobStatus.RUNNING
    assert restored.current_version == 1


def test_write_state_overwrites_existing(tmp_path, sample_state):
    write_state(tmp_path, sample_state)
    updated = sample_state.model_copy(update={"current_version": 3})
    write_state(tmp_path, updated)
    restored = read_state(tmp_path)
    assert restored.current_version == 3


# ── write_output_files ───────────────────────────────────────────────────────

def test_write_output_files_writes_to_project_root(tmp_path, sample_generation):
    write_output_files(sample_generation, project_root=tmp_path)
    assert (tmp_path / "src" / "utils.c").exists()
    assert "binary_search" in (tmp_path / "src" / "utils.c").read_text()


def test_write_output_files_returns_list_of_written_paths(tmp_path, sample_generation):
    written = write_output_files(sample_generation, project_root=tmp_path)
    assert written == ["src/utils.c"]


def test_write_output_files_creates_nested_dirs(tmp_path):
    gen = GenerationResult(
        subtasks=[
            GeneratedCode(
                subtask_id="s1", language="python",
                file_path="src/lib/helpers.py",
                code="def helper(): pass", explanation="", confidence=0.9,
            )
        ]
    )
    write_output_files(gen, project_root=tmp_path)
    assert (tmp_path / "src" / "lib" / "helpers.py").exists()


def test_write_output_files_multiple_subtasks(tmp_path):
    gen = GenerationResult(
        subtasks=[
            GeneratedCode(subtask_id="s1", language="python", file_path="src/foo.py",
                          code="x=1", explanation="", confidence=0.9),
            GeneratedCode(subtask_id="s2", language="python", file_path="tests/test_foo.py",
                          code="def test(): pass", explanation="", confidence=0.9),
        ]
    )
    written = write_output_files(gen, project_root=tmp_path)
    assert set(written) == {"src/foo.py", "tests/test_foo.py"}
    assert (tmp_path / "src" / "foo.py").exists()
    assert (tmp_path / "tests" / "test_foo.py").exists()


# ── read_plan ─────────────────────────────────────────────────────────────────

def test_read_plan_returns_plan_object(tmp_path, sample_plan):
    version_dir = tmp_path / "v1"
    write_plan(version_dir, sample_plan)
    restored = read_plan(version_dir)
    assert isinstance(restored, Plan)
    assert restored.task_id == "task-1"
    assert len(restored.subtasks) == 1
