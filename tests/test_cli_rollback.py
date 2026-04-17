from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from aspectcoder.cli import app


runner = CliRunner()


def test_rollback_command_exits_zero_on_success(tmp_path):
    with patch("aspectcoder.cli.commands.rollback.TaskManager") as MockTM:
        mock_tm = MagicMock()
        mock_tm.rollback.return_value = ["src/utils.c"]
        MockTM.return_value = mock_tm
        result = runner.invoke(app, ["rollback", "abc123", "--version", "1"])
    assert result.exit_code == 0


def test_rollback_command_prints_restored_files(tmp_path):
    with patch("aspectcoder.cli.commands.rollback.TaskManager") as MockTM:
        mock_tm = MagicMock()
        mock_tm.rollback.return_value = ["src/utils.c", "tests/test_utils.c"]
        MockTM.return_value = mock_tm
        result = runner.invoke(app, ["rollback", "abc123", "--version", "2"])
    assert "src/utils.c" in result.output
    assert "tests/test_utils.c" in result.output


def test_rollback_command_exits_nonzero_on_missing_version(tmp_path):
    with patch("aspectcoder.cli.commands.rollback.TaskManager") as MockTM:
        mock_tm = MagicMock()
        mock_tm.rollback.side_effect = FileNotFoundError("version not found")
        MockTM.return_value = mock_tm
        result = runner.invoke(app, ["rollback", "abc123", "--version", "99"])
    assert result.exit_code != 0
