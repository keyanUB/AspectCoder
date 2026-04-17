from __future__ import annotations
from pathlib import Path
from typing import Annotated, List, Optional

import typer

from aspectcoder.config import load_config
from aspectcoder.pipeline.orchestrator import Orchestrator, HumanNeededError, VALID_REVIEWERS
from aspectcoder.agents.reviewers.security import SecurityLevel
from aspectcoder.storage.task_manager import TaskManager
from aspectcoder.storage.report import write_report
from aspectcoder.storage.snapshot import write_output_files


def run_command(
    task: Annotated[Optional[str], typer.Argument(help="Task description")] = None,
    file: Annotated[Optional[Path], typer.Option("--file", "-f", help="Read task from a markdown file")] = None,
    config_path: Annotated[Path, typer.Option("--config", "-c", help="Path to config.yaml")] = Path("config.yaml"),
    reviewer: Annotated[
        Optional[List[str]],
        typer.Option(
            "--reviewer",
            help="Reviewer(s) to run: functional, security, performance. "
                 "Repeat to include multiple. Use 'none' to skip all reviews. "
                 "Default: all three.",
        ),
    ] = None,
    security_level: Annotated[
        SecurityLevel,
        typer.Option(
            "--security-level",
            help="Security review depth: basic (obvious issues), standard (CWE Top 25), "
                 "strict (CWE Top 25 + OWASP Secure Coding Practices).",
        ),
    ] = SecurityLevel.STANDARD,
) -> None:
    """
    Run the multi-agent pipeline on a coding task.

    Accepts a task description inline or from a Markdown file (--file).
    The pipeline plans, generates, reviews (functional / security / performance),
    and writes the resulting code into the project directory.

    Examples:

      aspectcoder run "Add binary search to utils.c"

      aspectcoder run --file demo/python-lru-cache.md

      aspectcoder run --file task.md --reviewer functional --reviewer security

      aspectcoder run --file task.md --reviewer none

      aspectcoder run --file task.md --security-level strict
    """
    # Validate reviewer names
    enabled_reviewers: set[str] | None = None
    if reviewer:
        if reviewer == ["none"]:
            enabled_reviewers = set()
        else:
            invalid = [r for r in reviewer if r not in VALID_REVIEWERS]
            if invalid:
                raise typer.BadParameter(
                    f"Invalid reviewer(s): {', '.join(invalid)}. "
                    f"Valid choices: {', '.join(sorted(VALID_REVIEWERS))}, none.",
                    param_hint="'--reviewer'",
                )
            enabled_reviewers = set(reviewer)

    if file is not None:
        task_description = file.read_text().strip()
    elif task:
        task_description = task
    else:
        typer.echo("Provide a task description or --file.", err=True)
        raise typer.Exit(code=1)

    config = load_config(config_path)
    tm = TaskManager()
    state = tm.create_job(task_description)
    typer.echo(f"Job {state.job_id} started.")

    try:
        orchestrator = Orchestrator(
            config=config,
            progress=typer.echo,
            enabled_reviewers=enabled_reviewers,
            security_level=security_level,
        )
        result = orchestrator.run(task_description, codebase_context="")

        state = tm.snapshot_plan(state, result.plan)
        state = tm.snapshot_code(state, result.generated_code)

        for attempt in result.all_attempts:
            for verdict in attempt.verdicts:
                state = tm.add_verdict(state, verdict)

        state = tm.complete_job(state)

        written = write_output_files(result.generated_code, project_root=Path.cwd())
        for path in written:
            typer.echo(f"  wrote {path}")

        job_dir = tm.job_dir(state.job_id)
        write_report(job_dir, state, result.plan, result.generated_code, result.decision, project_root=Path.cwd())

        typer.echo(f"✓ Done  · job {state.job_id} · {len(written)} file(s) written")

    except HumanNeededError as exc:
        state = tm.fail_job(state)
        typer.echo(f"⚠ Human input needed: {exc}", err=True)
        raise typer.Exit(code=1)
