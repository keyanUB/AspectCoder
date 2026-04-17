import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from aspectcoder.cli import app
from aspectcoder.models.aggregator import AggregatorAction, AggregatorDecision
from aspectcoder.models.code import GeneratedCode, GenerationResult
from aspectcoder.models.job import JobState, JobStatus, VerdictRecord
from aspectcoder.models.plan import Plan, Subtask
from aspectcoder.models.verdict import ReviewVerdict, ReviewerType
from aspectcoder.pipeline.orchestrator import OrchestratorResult


runner = CliRunner()


def _sample_plan() -> Plan:
    return Plan(
        task_id="task-1",
        task_description="Add binary_search",
        approach="Iterative",
        subtasks=[Subtask(id="s1", description="Impl", target_file="src/utils.c", language="c")],
        target_files=["src/utils.c"],
        primary_language="c",
        confidence=0.9,
    )


def _sample_generation() -> GenerationResult:
    return GenerationResult(
        subtasks=[
            GeneratedCode(
                subtask_id="s1", language="c", file_path="src/utils.c",
                code="int f(){}", explanation="", confidence=0.9,
            )
        ]
    )


def _sample_result() -> OrchestratorResult:
    from aspectcoder.models.aggregator import AttemptSummary
    return OrchestratorResult(
        plan=_sample_plan(),
        generated_code=_sample_generation(),
        decision=AggregatorDecision(action=AggregatorAction.DONE, summary="All passed."),
        all_attempts=[],
    )


def _make_state(job_id: str = "abc123") -> JobState:
    now = datetime.now(timezone.utc)
    return JobState(
        job_id=job_id, task_description="Add binary_search",
        status=JobStatus.DONE, current_version=2,
        created_at=now, updated_at=now,
    )


# ── aspectcoder run <task> ────────────────────────────────────────────────────────

def test_run_command_exits_zero_on_success(tmp_path):
    result_obj = _sample_result()
    state = _make_state()

    with patch("aspectcoder.cli.commands.run.load_config"), \
         patch("aspectcoder.cli.commands.run.TaskManager") as MockTM, \
         patch("aspectcoder.cli.commands.run.Orchestrator") as MockOrch, \
         patch("aspectcoder.cli.commands.run.write_report"):

        mock_tm = MagicMock()
        mock_tm.create_job.return_value = state
        mock_tm.snapshot_plan.return_value = state
        mock_tm.snapshot_code.return_value = state
        mock_tm.add_verdict.return_value = state
        mock_tm.complete_job.return_value = state
        MockTM.return_value = mock_tm

        mock_orch = MagicMock()
        mock_orch.run.return_value = result_obj
        MockOrch.return_value = mock_orch

        result = runner.invoke(app, ["run", "Add binary_search"])

    assert result.exit_code == 0


def test_run_command_prints_job_id_on_success(tmp_path):
    result_obj = _sample_result()
    state = _make_state("abc123")

    with patch("aspectcoder.cli.commands.run.load_config"), \
         patch("aspectcoder.cli.commands.run.TaskManager") as MockTM, \
         patch("aspectcoder.cli.commands.run.Orchestrator") as MockOrch, \
         patch("aspectcoder.cli.commands.run.write_report"):

        mock_tm = MagicMock()
        mock_tm.create_job.return_value = state
        mock_tm.snapshot_plan.return_value = state
        mock_tm.snapshot_code.return_value = state
        mock_tm.add_verdict.return_value = state
        mock_tm.complete_job.return_value = state
        MockTM.return_value = mock_tm

        mock_orch = MagicMock()
        mock_orch.run.return_value = result_obj
        MockOrch.return_value = mock_orch

        result = runner.invoke(app, ["run", "Add binary_search"])

    assert "abc123" in result.output


def test_run_command_calls_orchestrator_with_task(tmp_path):
    result_obj = _sample_result()
    state = _make_state()

    with patch("aspectcoder.cli.commands.run.load_config"), \
         patch("aspectcoder.cli.commands.run.TaskManager") as MockTM, \
         patch("aspectcoder.cli.commands.run.Orchestrator") as MockOrch, \
         patch("aspectcoder.cli.commands.run.write_report"):

        mock_tm = MagicMock()
        mock_tm.create_job.return_value = state
        mock_tm.snapshot_plan.return_value = state
        mock_tm.snapshot_code.return_value = state
        mock_tm.complete_job.return_value = state
        MockTM.return_value = mock_tm

        mock_orch = MagicMock()
        mock_orch.run.return_value = result_obj
        MockOrch.return_value = mock_orch

        runner.invoke(app, ["run", "Add binary_search to utils.c"])

    mock_orch.run.assert_called_once_with("Add binary_search to utils.c", codebase_context="")


def test_run_command_exits_nonzero_on_human_needed(tmp_path):
    from aspectcoder.pipeline.orchestrator import HumanNeededError

    state = _make_state()

    with patch("aspectcoder.cli.commands.run.load_config"), \
         patch("aspectcoder.cli.commands.run.TaskManager") as MockTM, \
         patch("aspectcoder.cli.commands.run.Orchestrator") as MockOrch, \
         patch("aspectcoder.cli.commands.run.write_report"):

        mock_tm = MagicMock()
        mock_tm.create_job.return_value = state
        mock_tm.fail_job.return_value = state
        MockTM.return_value = mock_tm

        mock_orch = MagicMock()
        mock_orch.run.side_effect = HumanNeededError("task is ambiguous")
        MockOrch.return_value = mock_orch

        result = runner.invoke(app, ["run", "vague task"])

    assert result.exit_code != 0
    assert "human" in result.output.lower() or "ambiguous" in result.output.lower()


def test_run_command_reads_task_from_file(tmp_path):
    task_file = tmp_path / "task.md"
    task_file.write_text("Add binary_search to utils.c")
    result_obj = _sample_result()
    state = _make_state()

    with patch("aspectcoder.cli.commands.run.load_config"), \
         patch("aspectcoder.cli.commands.run.TaskManager") as MockTM, \
         patch("aspectcoder.cli.commands.run.Orchestrator") as MockOrch, \
         patch("aspectcoder.cli.commands.run.write_report"):

        mock_tm = MagicMock()
        mock_tm.create_job.return_value = state
        mock_tm.snapshot_plan.return_value = state
        mock_tm.snapshot_code.return_value = state
        mock_tm.complete_job.return_value = state
        MockTM.return_value = mock_tm

        mock_orch = MagicMock()
        mock_orch.run.return_value = result_obj
        MockOrch.return_value = mock_orch

        runner.invoke(app, ["run", "--file", str(task_file)])

    mock_orch.run.assert_called_once_with("Add binary_search to utils.c", codebase_context="")


# ── Reviewer selection via --reviewer flag ────────────────────────────────────

def _wire_tm(MockTM, state):
    mock_tm = MagicMock()
    mock_tm.create_job.return_value = state
    mock_tm.snapshot_plan.return_value = state
    mock_tm.snapshot_code.return_value = state
    mock_tm.add_verdict.return_value = state
    mock_tm.complete_job.return_value = state
    MockTM.return_value = mock_tm
    return mock_tm


def test_run_no_reviewer_flag_passes_none_to_orchestrator():
    result_obj = _sample_result()
    state = _make_state()

    with patch("aspectcoder.cli.commands.run.load_config"), \
         patch("aspectcoder.cli.commands.run.TaskManager") as MockTM, \
         patch("aspectcoder.cli.commands.run.Orchestrator") as MockOrch, \
         patch("aspectcoder.cli.commands.run.write_report"):
        _wire_tm(MockTM, state)
        mock_orch = MagicMock()
        mock_orch.run.return_value = result_obj
        MockOrch.return_value = mock_orch

        runner.invoke(app, ["run", "Add binary_search"])

    _, kwargs = MockOrch.call_args
    assert kwargs["enabled_reviewers"] is None


def test_run_single_reviewer_flag_passes_correct_set():
    result_obj = _sample_result()
    state = _make_state()

    with patch("aspectcoder.cli.commands.run.load_config"), \
         patch("aspectcoder.cli.commands.run.TaskManager") as MockTM, \
         patch("aspectcoder.cli.commands.run.Orchestrator") as MockOrch, \
         patch("aspectcoder.cli.commands.run.write_report"):
        _wire_tm(MockTM, state)
        mock_orch = MagicMock()
        mock_orch.run.return_value = result_obj
        MockOrch.return_value = mock_orch

        runner.invoke(app, ["run", "--reviewer", "functional", "Add binary_search"])

    _, kwargs = MockOrch.call_args
    assert kwargs["enabled_reviewers"] == {"functional"}


def test_run_multiple_reviewer_flags_build_correct_set():
    result_obj = _sample_result()
    state = _make_state()

    with patch("aspectcoder.cli.commands.run.load_config"), \
         patch("aspectcoder.cli.commands.run.TaskManager") as MockTM, \
         patch("aspectcoder.cli.commands.run.Orchestrator") as MockOrch, \
         patch("aspectcoder.cli.commands.run.write_report"):
        _wire_tm(MockTM, state)
        mock_orch = MagicMock()
        mock_orch.run.return_value = result_obj
        MockOrch.return_value = mock_orch

        runner.invoke(
            app,
            ["run", "--reviewer", "security", "--reviewer", "performance", "Add binary_search"],
        )

    _, kwargs = MockOrch.call_args
    assert kwargs["enabled_reviewers"] == {"security", "performance"}


def test_run_invalid_reviewer_exits_with_error():
    result = runner.invoke(app, ["run", "--reviewer", "linting", "Add binary_search"])
    assert result.exit_code != 0
    assert "linting" in result.output or "invalid" in result.output.lower()


# ── Security level flag ───────────────────────────────────────────────────────

def test_run_default_security_level_passes_standard_to_orchestrator():
    from aspectcoder.agents.reviewers.security import SecurityLevel
    result_obj = _sample_result()
    state = _make_state()

    with patch("aspectcoder.cli.commands.run.load_config"), \
         patch("aspectcoder.cli.commands.run.TaskManager") as MockTM, \
         patch("aspectcoder.cli.commands.run.Orchestrator") as MockOrch, \
         patch("aspectcoder.cli.commands.run.write_report"), \
         patch("aspectcoder.cli.commands.run.write_output_files", return_value=[]):
        _wire_tm(MockTM, state)
        mock_orch = MagicMock()
        mock_orch.run.return_value = result_obj
        MockOrch.return_value = mock_orch

        runner.invoke(app, ["run", "Add binary_search"])

    _, kwargs = MockOrch.call_args
    assert kwargs["security_level"] == SecurityLevel.STANDARD


def test_run_strict_security_level_flag_passes_strict_to_orchestrator():
    from aspectcoder.agents.reviewers.security import SecurityLevel
    result_obj = _sample_result()
    state = _make_state()

    with patch("aspectcoder.cli.commands.run.load_config"), \
         patch("aspectcoder.cli.commands.run.TaskManager") as MockTM, \
         patch("aspectcoder.cli.commands.run.Orchestrator") as MockOrch, \
         patch("aspectcoder.cli.commands.run.write_report"), \
         patch("aspectcoder.cli.commands.run.write_output_files", return_value=[]):
        _wire_tm(MockTM, state)
        mock_orch = MagicMock()
        mock_orch.run.return_value = result_obj
        MockOrch.return_value = mock_orch

        runner.invoke(app, ["run", "--security-level", "strict", "Add binary_search"])

    _, kwargs = MockOrch.call_args
    assert kwargs["security_level"] == SecurityLevel.STRICT


def test_run_invalid_security_level_exits_with_error():
    result = runner.invoke(app, ["run", "--security-level", "extreme", "Add binary_search"])
    assert result.exit_code != 0
