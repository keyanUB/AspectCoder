from __future__ import annotations
from pathlib import Path
from typing import Annotated

import typer

from aspectcoder.storage.task_manager import TaskManager


def status_command(
    job_id: Annotated[str, typer.Argument(help="Job ID to inspect")],
) -> None:
    """
    Show the current status of a job.

    Prints task description, status (running / done / failed), current snapshot
    version, retry counts, and timestamps.

    Example:

      aspectcoder status abc12345
    """
    tm = TaskManager()
    try:
        state = tm.get_job(job_id)
    except FileNotFoundError:
        typer.echo(f"Job '{job_id}' not found.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Job:         {state.job_id}")
    typer.echo(f"Task:        {state.task_description}")
    typer.echo(f"Status:      {state.status.value}")
    typer.echo(f"Version:     v{state.current_version}")
    typer.echo(f"Retries:     verifier={state.verifier_retries}  regen={state.regen_retries}  replan={state.replan_retries}")
    typer.echo(f"Created:     {state.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    typer.echo(f"Updated:     {state.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
