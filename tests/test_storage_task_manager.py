import json
from pathlib import Path
import pytest

from aspectcoder.storage.task_manager import TaskManager
from aspectcoder.storage.snapshot import read_state, read_plan
from aspectcoder.models.plan import Plan, Subtask
from aspectcoder.models.verdict import PlanVerdict, ReviewVerdict, ReviewerType, Issue, IssueSeverity
from aspectcoder.models.code import GenerationResult, GeneratedCode
from aspectcoder.models.job import JobStatus


@pytest.fixture
def manager(tmp_path):
    return TaskManager(jobs_dir=tmp_path / "jobs")


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
def sample_generation():
    return GenerationResult(
        subtasks=[
            GeneratedCode(
                subtask_id="subtask-1",
                language="c",
                file_path="src/utils.c",
                code="int binary_search() { return 0; }",
                explanation="Done",
                confidence=0.85,
            )
        ]
    )


# ── create_job ────────────────────────────────────────────────────────────────

def test_job_dir_returns_correct_path(manager):
    state = manager.create_job("task")
    assert manager.job_dir(state.job_id) == manager.jobs_dir / state.job_id


def test_create_job_returns_running_state(manager):
    state = manager.create_job("Add binary_search")
    assert state.status == JobStatus.RUNNING
    assert state.task_description == "Add binary_search"
    assert state.current_version == 0
    assert len(state.job_id) > 0


def test_create_job_writes_state_to_disk(manager):
    state = manager.create_job("task")
    job_dir = manager.jobs_dir / state.job_id
    assert (job_dir / "state.json").exists()
    restored = read_state(job_dir)
    assert restored.job_id == state.job_id


# ── snapshot_plan ─────────────────────────────────────────────────────────────

def test_snapshot_plan_increments_version(manager, sample_plan):
    state = manager.create_job("task")
    assert state.current_version == 0
    state = manager.snapshot_plan(state, sample_plan)
    assert state.current_version == 1


def test_snapshot_plan_writes_plan_json(manager, sample_plan):
    state = manager.create_job("task")
    state = manager.snapshot_plan(state, sample_plan)
    job_dir = manager.jobs_dir / state.job_id
    plan_file = job_dir / "v1" / "plan.json"
    assert plan_file.exists()
    data = json.loads(plan_file.read_text())
    assert data["task_id"] == "task-1"


def test_snapshot_plan_writes_verdict_when_provided(manager, sample_plan):
    verdict = PlanVerdict(pass_=True, confidence=0.9, issues=[])
    state = manager.create_job("task")
    state = manager.snapshot_plan(state, sample_plan, verdict=verdict)
    job_dir = manager.jobs_dir / state.job_id
    assert (job_dir / "v1" / "plan_verdict.json").exists()


def test_snapshot_plan_updates_state_on_disk(manager, sample_plan):
    state = manager.create_job("task")
    state = manager.snapshot_plan(state, sample_plan)
    job_dir = manager.jobs_dir / state.job_id
    disk_state = read_state(job_dir)
    assert disk_state.current_version == 1


# ── snapshot_code ─────────────────────────────────────────────────────────────

def test_snapshot_code_increments_version(manager, sample_plan, sample_generation):
    state = manager.create_job("task")
    state = manager.snapshot_plan(state, sample_plan)
    state = manager.snapshot_code(state, sample_generation)
    assert state.current_version == 2


def test_snapshot_code_writes_code_files(manager, sample_plan, sample_generation):
    state = manager.create_job("task")
    state = manager.snapshot_plan(state, sample_plan)
    state = manager.snapshot_code(state, sample_generation)
    job_dir = manager.jobs_dir / state.job_id
    code_file = job_dir / "v2" / "code" / "src" / "utils.c"
    assert code_file.exists()
    assert "binary_search" in code_file.read_text()


def test_snapshot_code_copies_current_plan_for_reference(manager, sample_plan, sample_generation):
    state = manager.create_job("task")
    state = manager.snapshot_plan(state, sample_plan)
    state = manager.snapshot_code(state, sample_generation)
    job_dir = manager.jobs_dir / state.job_id
    assert (job_dir / "v2" / "plan.json").exists()


# ── snapshot_attempt ─────────────────────────────────────────────────────────

def test_snapshot_attempt_increments_version(manager, sample_plan, sample_generation):
    state = manager.create_job("task")
    state = manager.snapshot_plan(state, sample_plan)
    verdict = ReviewVerdict(reviewer=ReviewerType.FUNCTIONAL, pass_=True, confidence=0.9)
    state = manager.snapshot_attempt(state, sample_generation, [verdict])
    assert state.current_version == 2


def test_snapshot_attempt_saves_code_files(manager, sample_plan, sample_generation):
    state = manager.create_job("task")
    state = manager.snapshot_plan(state, sample_plan)
    verdict = ReviewVerdict(reviewer=ReviewerType.FUNCTIONAL, pass_=True, confidence=0.9)
    state = manager.snapshot_attempt(state, sample_generation, [verdict])
    job_dir = manager.jobs_dir / state.job_id
    assert (job_dir / "v2" / "code" / "src" / "utils.c").exists()


def test_snapshot_attempt_saves_verdicts_json(manager, sample_plan, sample_generation):
    state = manager.create_job("task")
    state = manager.snapshot_plan(state, sample_plan)
    issue = Issue(
        severity=IssueSeverity.MAJOR,
        description="Missing null check",
        location="utils.c:5",
        suggestion="Add null guard",
    )
    verdict = ReviewVerdict(reviewer=ReviewerType.SECURITY, pass_=False, confidence=0.7, issues=[issue])
    state = manager.snapshot_attempt(state, sample_generation, [verdict])
    job_dir = manager.jobs_dir / state.job_id
    verdicts_file = job_dir / "v2" / "verdicts.json"
    assert verdicts_file.exists()
    data = json.loads(verdicts_file.read_text())
    assert data[0]["reviewer"] == "security"
    assert data[0]["issues"][0]["description"] == "Missing null check"
    assert data[0]["issues"][0]["severity"] == "major"
    assert data[0]["issues"][0]["suggestion"] == "Add null guard"


def test_snapshot_attempt_appends_verdicts_to_state(manager, sample_plan, sample_generation):
    state = manager.create_job("task")
    state = manager.snapshot_plan(state, sample_plan)
    verdict = ReviewVerdict(reviewer=ReviewerType.PERFORMANCE, pass_=False, confidence=0.6)
    state = manager.snapshot_attempt(state, sample_generation, [verdict])
    assert len(state.verdicts) == 1
    assert state.verdicts[0].reviewer == "performance"


# ── add_verdict ───────────────────────────────────────────────────────────────

def test_add_verdict_appends_to_state(manager):
    state = manager.create_job("task")
    verdict = ReviewVerdict(reviewer=ReviewerType.SECURITY, pass_=False, confidence=0.7)
    state = manager.add_verdict(state, verdict)
    assert len(state.verdicts) == 1
    assert state.verdicts[0].reviewer == "security"
    assert state.verdicts[0].pass_ is False


def test_add_verdict_persists_to_disk(manager):
    state = manager.create_job("task")
    verdict = ReviewVerdict(reviewer=ReviewerType.FUNCTIONAL, pass_=True, confidence=0.9)
    state = manager.add_verdict(state, verdict)
    job_dir = manager.jobs_dir / state.job_id
    disk_state = read_state(job_dir)
    assert len(disk_state.verdicts) == 1
    assert disk_state.verdicts[0].reviewer == "functional"


# ── complete_job / fail_job ───────────────────────────────────────────────────

def test_complete_job_sets_status_done(manager):
    state = manager.create_job("task")
    state = manager.complete_job(state)
    assert state.status == JobStatus.DONE
    job_dir = manager.jobs_dir / state.job_id
    assert read_state(job_dir).status == JobStatus.DONE


def test_fail_job_sets_status_failed(manager):
    state = manager.create_job("task")
    state = manager.fail_job(state)
    assert state.status == JobStatus.FAILED
    job_dir = manager.jobs_dir / state.job_id
    assert read_state(job_dir).status == JobStatus.FAILED


# ── rollback ──────────────────────────────────────────────────────────────────

def test_rollback_copies_code_files_to_project(manager, sample_plan, sample_generation, tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()

    state = manager.create_job("task")
    state = manager.snapshot_plan(state, sample_plan)
    state = manager.snapshot_code(state, sample_generation)

    restored = manager.rollback(state.job_id, version=2, project_root=project_root)

    dest = project_root / "src" / "utils.c"
    assert dest.exists()
    assert "binary_search" in dest.read_text()
    assert "src/utils.c" in restored


def test_rollback_backs_up_existing_files(manager, sample_plan, sample_generation, tmp_path):
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)
    (project_root / "src" / "utils.c").write_text("// original content")

    state = manager.create_job("task")
    state = manager.snapshot_plan(state, sample_plan)
    state = manager.snapshot_code(state, sample_generation)

    manager.rollback(state.job_id, version=2, project_root=project_root)

    job_dir = manager.jobs_dir / state.job_id
    backup = job_dir / "pre-rollback" / "src" / "utils.c"
    assert backup.exists()
    assert backup.read_text() == "// original content"
