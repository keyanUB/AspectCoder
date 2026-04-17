from __future__ import annotations
from pathlib import Path

from aspectcoder.models.job import JobState
from aspectcoder.models.plan import Plan
from aspectcoder.models.code import GenerationResult
from aspectcoder.models.aggregator import AggregatorDecision, AttemptSummary


def write_report(
    job_dir: Path,
    state: JobState,
    plan: Plan,
    generated: GenerationResult,
    decision: AggregatorDecision,
    project_root: Path | None = None,
    all_attempts: list[AttemptSummary] | None = None,
) -> Path:
    regen_count = state.regen_retries
    regen_note = f"{regen_count} regeneration{'s' if regen_count != 1 else ''}" if regen_count else "no regenerations"

    files_changed = "\n".join(
        f"- `{subtask.file_path}`" for subtask in generated.subtasks
    )

    versions_section = "\n".join(
        f"- v{v}: `{job_dir}/v{v}/`" for v in range(1, state.current_version + 1)
    )

    failed = [r for r in state.verdicts if not r.pass_]
    issues_section = ""
    if failed:
        lines = []
        for r in failed:
            for issue in r.issues:
                lines.append(f"- [{r.reviewer.upper()} v{r.version}] {issue}")
        issues_section = "## Issues Found\n" + "\n".join(lines) + "\n\n"

    verdicts_by_version: dict[int, list] = {}
    for r in state.verdicts:
        verdicts_by_version.setdefault(r.version, []).append(r)

    review_rows = []
    for version, records in sorted(verdicts_by_version.items()):
        for r in records:
            status = "✓" if r.pass_ else "✗"
            review_rows.append(f"| {r.reviewer.capitalize()} (v{version}) | {status} |")
    review_table = (
        "| Reviewer | Result |\n|---|---|\n" + "\n".join(review_rows)
        if review_rows else "_No verdicts recorded._"
    )

    detail_section = ""
    if all_attempts:
        lines = ["## Review Detail\n"]
        for attempt in all_attempts:
            lines.append(f"### Attempt {attempt.attempt_number}\n")
            for v in attempt.verdicts:
                status = "Pass" if v.pass_ else "Fail"
                lines.append(f"**{v.reviewer.value.capitalize()}** — {status} (confidence: {v.confidence:.0%})\n")
                for issue in v.issues:
                    loc = f" `{issue.location}`" if issue.location else ""
                    lines.append(f"- **[{issue.severity.value.upper()}]**{loc} {issue.description}")
                    lines.append(f"  - *Suggestion:* {issue.suggestion}")
                if not v.issues:
                    lines.append("_No issues._")
                lines.append("")
        detail_section = "\n".join(lines) + "\n"

    content = f"""\
# AspectCoder Run Report — {state.job_id}

**Task:** {state.task_description}
**Status:** {state.status.value.capitalize()}
**Versions:** {state.current_version} ({regen_note})

## Files Changed
{files_changed}

## Review Summary
{review_table}

{issues_section}{detail_section}## Versions
{versions_section}
"""

    report_path = job_dir / "report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content)

    if project_root is not None:
        copy_path = project_root / "reports" / f"{state.job_id}.md"
        copy_path.parent.mkdir(parents=True, exist_ok=True)
        copy_path.write_text(content)

    return report_path
