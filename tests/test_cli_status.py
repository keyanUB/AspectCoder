from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from aspectcoder.cli import app
from aspectcoder.models.job import JobState, JobStatus


runner = CliRunner()


def _make_state(job_id: str = "abc123", status: JobStatus = JobStatus.DONE) -> JobState:
    now = datetime.now(timezone.utc)
    return JobState(
        job_id=job_id, task_description="Add binary_search",
        status=status, current_version=2,
        created_at=now, updated_at=now,
    )


def test_status_command_exits_zero(tmp_path):
    state = _make_state()
    with patch("aspectcoder.cli.commands.status.TaskManager") as MockTM:
        mock_tm = MagicMock()
        mock_tm.get_job.return_value = state
        MockTM.return_value = mock_tm
        result = runner.invoke(app, ["status", "abc123"])
    assert result.exit_code == 0


def test_status_command_prints_job_id_and_status(tmp_path):
    state = _make_state("abc123", JobStatus.DONE)
    with patch("aspectcoder.cli.commands.status.TaskManager") as MockTM:
        mock_tm = MagicMock()
        mock_tm.get_job.return_value = state
        MockTM.return_value = mock_tm
        result = runner.invoke(app, ["status", "abc123"])
    assert "abc123" in result.output
    assert "done" in result.output.lower()


def test_status_command_exits_nonzero_for_unknown_job(tmp_path):
    with patch("aspectcoder.cli.commands.status.TaskManager") as MockTM:
        mock_tm = MagicMock()
        mock_tm.get_job.side_effect = FileNotFoundError("not found")
        MockTM.return_value = mock_tm
        result = runner.invoke(app, ["status", "unknown"])
    assert result.exit_code != 0
