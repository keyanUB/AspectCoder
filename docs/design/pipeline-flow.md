# Pipeline Flow

## Overview

The pipeline runs as a directed acyclic graph (DAG) orchestrated by the DAG Orchestrator. Agents are nodes; the Orchestrator controls which node runs next based on the previous node's output.

```
User Task
   │
   ▼
Task Manager ──────────────────────────────────────────── creates job, owns state
   │
   ▼
┌─────────────────── PLANNING PHASE ──────────────────────┐
│  Planner ──→ Plan Verifier                               │
│      ↑____________| (on fail, up to 3× replans)          │
└──────────────────────────────────────────────────────────┘
   │ (plan approved)
   ▼
┌─────────────────── GENERATION PHASE ───────────────────┐
│  Generator                                              │
└─────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────── REVIEW PHASE ───────────────────────┐
│  1. Functional Reviewer                                 │
│     ├── FAIL → early exit (skip Security + Perf)       │
│     └── PASS ↓                                         │
│  2. Security Reviewer  ┐ run in parallel               │
│  3. Perf Reviewer      ┘                               │
│     └── any FAIL / all PASS → Aggregator               │
└─────────────────────────────────────────────────────────┘
   │
   ▼
Aggregator ──→ routing decision (see below)
   │
   ▼
Output Manager ──→ write files + report
```

---

## Phase Details

### Planning Phase

1. **Planner** receives the task description and codebase context. Produces a `Plan` object: subtask list, approach, target files, primary language.
2. **Plan Verifier** is a one-shot judge — it does not retry. It reads the Plan and emits a `PlanVerdict` (pass/fail, confidence, issues list).
3. If the verdict fails, issues are sent back to the Planner which revises and resubmits. The Planner may revise up to **3 times** before the Human Loop is triggered.

### Generation Phase

1. **Generator** receives the approved Plan and produces `GeneratedCode` for each subtask.
2. Language-aware model selection applies here: C and C++ tasks use a stronger model than Python and JavaScript. See `llm-config.md`.

### Review Phase

Reviews run **sequentially with early exit**:

1. **Functional Reviewer** always runs first. If it fails, Security and Performance reviewers are skipped entirely — the failure goes straight to the Aggregator.
2. If Functional passes, **Security** and **Performance** reviewers run **in parallel**.
3. All reviewer outputs are collected by the **Aggregator**.

---

## Routing & Retry Logic

### Replan vs. Regenerate

The core question after a review failure: *is the approach wrong, or is the implementation wrong?*

| Condition | Action |
|---|---|
| Any reviewer sets `approach_wrong: true` | Replan immediately |
| Generator confidence < 0.4 | Replan immediately (plan is unimplementable) |
| Specific bugs / vulnerabilities / inefficiencies | Regenerate with reviewer feedback |

### Retry Budgets

| Stage | Retry limit |
|---|---|
| Planner (revision on Verifier fail) | 3× |
| Generator (regeneration on review fail) | 3× |
| Replan cycles (after regen budget exhausted) | 3× |

### Regeneration Exhaustion → Replan

If the Generator fails 3 consecutive review cycles without passing:

1. The Aggregator compiles a **Failure Report** (see `data-models.md`)
2. The Failure Report is sent to the Planner to trigger a replan
3. After replanning, the Generator resets its retry count and tries again
4. The Planner may replan up to 3 times total

### Human Escalation

The Human Loop is triggered when:

- Any agent sets `needs_human: true` in its output (the LLM decides it cannot proceed alone)
- Aggregator sees any reviewer verdict with `confidence < 0.5` or `needs_human: true`
- Orchestrator sees `generator.confidence < 0.4` (plan is unimplementable)
- Planner retry budget exhausted (3 replans failed)
- Human input is requested and provided via CLI or Web UI, then the affected stage retries

Note: confidence-based routing is the orchestrator's or Aggregator's responsibility. `BaseAgent.last_needs_human` reflects only the output's explicit `needs_human` field — it does not apply a confidence threshold.

---

## Job Snapshots

At each of these points the Task Manager writes a snapshot to disk:

- After Planner produces a Plan (each version)
- After Generator produces code (each version)
- After each Aggregator decision

Snapshot location: `.mycoder/jobs/<job-id>/v<n>/`. See `storage.md` for full structure.
