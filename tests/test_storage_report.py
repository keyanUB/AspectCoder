from datetime import datetime, timezone
from pathlib import Path
import pytest

from aspectcoder.storage.report import write_report
from aspectcoder.models.job import JobState, JobStatus, VerdictRecord
from aspectcoder.models.plan import Plan, Subtask
from aspectcoder.models.code import GenerationResult, GeneratedCode
from aspectcoder.models.aggregator import AggregatorDecision, AggregatorAction


@pytest.fixture
def sample_state():
    now = datetime.now(timezone.utc)
    return JobState(
        job_id="abc123",
        task_description="Add binary_search to utils.c",
        status=JobStatus.DONE,
        current_version=2,
        regen_retries=1,
        created_at=now,
        updated_at=now,
        verdicts=[
            VerdictRecord(version=1, reviewer="security", pass_=False, issues=["Buffer overflow risk"]),
            VerdictRecord(version=2, reviewer="functional", pass_=True),
            VerdictRecord(version=2, reviewer="security", pass_=True),
            VerdictRecord(version=2, reviewer="performance", pass_=True),
        ],
    )


@pytest.fixture
def sample_plan():
    return Plan(
        task_id="task-1",
        task_description="Add binary_search to utils.c",
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
                code="int binary_search() {}",
                explanation="",
                confidence=0.9,
            )
        ]
    )


def test_write_report_creates_report_md(tmp_path, sample_state, sample_plan, sample_generation):
    decision = AggregatorDecision(action=AggregatorAction.DONE, summary="All passed.")
    report_path = write_report(tmp_path, sample_state, sample_plan, sample_generation, decision)
    assert report_path.exists()
    assert report_path.name == "report.md"


def test_report_contains_job_id_and_task(tmp_path, sample_state, sample_plan, sample_generation):
    decision = AggregatorDecision(action=AggregatorAction.DONE, summary="All passed.")
    report_path = write_report(tmp_path, sample_state, sample_plan, sample_generation, decision)
    content = report_path.read_text()
    assert "abc123" in content
    assert "binary_search" in content


def test_report_contains_files_changed(tmp_path, sample_state, sample_plan, sample_generation):
    decision = AggregatorDecision(action=AggregatorAction.DONE, summary="All passed.")
    report_path = write_report(tmp_path, sample_state, sample_plan, sample_generation, decision)
    content = report_path.read_text()
    assert "src/utils.c" in content


def test_report_lists_failed_verdicts_as_issues(tmp_path, sample_state, sample_plan, sample_generation):
    decision = AggregatorDecision(action=AggregatorAction.DONE, summary="All passed.")
    report_path = write_report(tmp_path, sample_state, sample_plan, sample_generation, decision)
    content = report_path.read_text()
    assert "Buffer overflow risk" in content


def test_report_shows_version_count(tmp_path, sample_state, sample_plan, sample_generation):
    decision = AggregatorDecision(action=AggregatorAction.DONE, summary="All passed.")
    report_path = write_report(tmp_path, sample_state, sample_plan, sample_generation, decision)
    content = report_path.read_text()
    assert "v1" in content
    assert "v2" in content


def test_write_report_copies_to_reports_dir(tmp_path, sample_state, sample_plan, sample_generation):
    project_root = tmp_path / "project"
    project_root.mkdir()
    job_dir = tmp_path / "job"
    decision = AggregatorDecision(action=AggregatorAction.DONE, summary="All passed.")
    write_report(job_dir, sample_state, sample_plan, sample_generation, decision, project_root=project_root)
    copy_path = project_root / "reports" / "abc123.md"
    assert copy_path.exists()
    assert "binary_search" in copy_path.read_text()
