from __future__ import annotations
from pathlib import Path
from typing import Annotated

import typer

from aspectcoder.storage.task_manager import TaskManager


def rollback_command(
    job_id: Annotated[str, typer.Argument(help="Job ID to roll back")],
    version: Annotated[int, typer.Option("--version", "-v", help="Snapshot version to restore")],
) -> None:
    """
    Restore a previous snapshot of a job's generated files.

    Copies the files from the requested snapshot version back into the project
    directory. The current files are backed up to .aspectcoder/jobs/<id>/pre-rollback/
    before being overwritten.

    Example:

      aspectcoder rollback abc12345 --version 1
    """
    tm = TaskManager()
    project_root = Path.cwd()

    try:
        restored = tm.rollback(job_id, version=version, project_root=project_root)
    except FileNotFoundError as exc:
        typer.echo(f"Rollback failed: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Restored {len(restored)} file(s) from job {job_id} v{version}:")
    for path in restored:
        typer.echo(f"  → {path}")
