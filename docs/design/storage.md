# Storage & Versioning

## Job Directory Structure

Every job gets its own directory under `.mycoder/jobs/<job-id>/`. The Task Manager writes a snapshot at each significant state transition so any version can be inspected or restored.

```
.mycoder/
  jobs/
    abc123/
      state.json          ← current JobState (updated after every change)
      report.md           ← final run report (written on completion)
      v1/                 ← first plan + first generated code
        plan.json
        plan_verdict.json
        code/
          utils.c
          test_utils.c
      v2/                 ← after Security Reviewer failed → regenerated
        plan.json         ← same plan (no replan), copied for reference
        code/
          utils.c         ← fixed version
          test_utils.c
      v3/                 ← hypothetical: after a replan
        plan.json         ← revised plan from Planner
        plan_verdict.json
        code/
          utils.c
          test_utils.c
```

### Version increment rules

| Event | New version? |
|---|---|
| Planner produces a new Plan | Yes |
| Generator produces new code (retry or first attempt) | Yes |
| Replan produces a revised Plan | Yes |
| Plan Verifier verdict (no code change) | No — appended to current version |
| Reviewer verdicts (no code change) | No — appended to current version |

---

## state.json

Written after every state change. Contains the full `JobState` schema (see `data-models.md`) plus a log of all verdicts.

```json
{
  "job_id": "abc123",
  "task_description": "add binary_search() to utils.c",
  "status": "done",
  "current_version": 2,
  "verifier_retries": 0,
  "regen_retries": 1,
  "replan_retries": 0,
  "created_at": "2026-04-16T10:00:00Z",
  "updated_at": "2026-04-16T10:00:18Z",
  "verdicts": [
    {"version": 1, "reviewer": "security", "pass": false, "issues": [...]},
    {"version": 2, "reviewer": "functional", "pass": true},
    {"version": 2, "reviewer": "security", "pass": true},
    {"version": 2, "reviewer": "performance", "pass": true}
  ]
}
```

---

## Rollback

To restore the codebase to a previous snapshot:

```bash
mycoder rollback abc123 --version 1
```

This copies the files from `.mycoder/jobs/abc123/v1/code/` back to their original locations in the project. The current files are backed up to `.mycoder/jobs/abc123/pre-rollback/` before overwriting.

Rollback does not resume the job — it only restores the files. To continue from a rolled-back state, run `mycoder resume abc123`.

---

## Report

On job completion, a markdown report is written to `.mycoder/jobs/<job-id>/report.md` and also copied to `reports/<job-id>.md` in the project root.

### Report structure

```markdown
# MyCoder Run Report — abc123

**Task:** add binary_search() to utils.c
**Status:** Done
**Duration:** 18.7s
**Versions:** 2 (1 regeneration)

## Files Changed
- `src/utils.c` — modified
- `tests/test_utils.c` — created

## Agent Summary
| Agent | Model | Result | Duration |
|---|---|---|---|
| Planner | claude-opus-4-7 | ✓ 3 subtasks | 3.1s |
| Plan Verifier | claude-sonnet-4-6 | ✓ approved | 1.2s |
| Generator (v1) | claude-opus-4-7 | ✓ | 5.4s |
| Security (v1) | claude-sonnet-4-6 | ✗ 1 major issue | 2.1s |
| Generator (v2) | claude-opus-4-7 | ✓ | 4.2s |
| Functional (v2) | gpt-5-mini | ✓ | 0.9s |
| Security (v2) | claude-sonnet-4-6 | ✓ | 1.8s |
| Performance (v2) | gpt-5-mini | ✓ | 0.8s |

## Issues Found & Resolved
- [MAJOR] Buffer overflow risk in binary_search() at utils.c:42 — fixed in v2

## Versions
- v1: `.mycoder/jobs/abc123/v1/`
- v2: `.mycoder/jobs/abc123/v2/` ← final
```

---

## .gitignore

Add `.mycoder/` to the project's `.gitignore` — job snapshots are local artifacts, not source code.

```
.mycoder/
.superpowers/
```
