# Interfaces

## CLI

Built with **Typer**. Streams agent progress to the terminal in real time via the same SSE events the Web UI consumes.

### Commands

| Command | Description |
|---|---|
| `mycoder run "task description"` | Run a task from a natural language string |
| `mycoder run --file task.md` | Run from a markdown task file |
| `mycoder status [job-id]` | Show status of current or past job |
| `mycoder resume [job-id]` | Resume an interrupted or waiting job |
| `mycoder logs [job-id]` | Stream full agent logs for a job |
| `mycoder rollback [job-id] --version N` | Restore job to a prior snapshot version |
| `mycoder config set` | Interactive prompt to set API keys and model overrides |
| `mycoder ui` | Start the Web UI server and open in browser |

### Terminal Output Format

```
$ mycoder run "add binary_search() to utils.c"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MyCoder  job abc123 · target: utils.c (C)

● Planner        [claude-opus-4-7]    thinking…
✓ Planner        [claude-opus-4-7]    3 subtasks · 2 files         (3.1s)
● Plan Verifier  [claude-sonnet-4-6]  checking…
✓ Plan Verifier  [claude-sonnet-4-6]  plan approved                (1.2s)

● Generator      [claude-opus-4-7 ↑C] writing utils.c…
✓ Generator      [claude-opus-4-7 ↑C] code ready                  (5.4s)

● Functional     [gpt-5-mini]         reviewing…
✓ Functional     [gpt-5-mini]         pass                         (1.0s)
● Security       [claude-sonnet-4-6]  reviewing…
✗ Security       [claude-sonnet-4-6]  1 issue                      (2.1s)
   └─ [MAJOR] Buffer overflow risk in binary_search() at line 42
      ↳ Performance skipped (early exit)

↻ Generator      [claude-opus-4-7]    fixing (attempt 2/3)…
✓ Generator      [claude-opus-4-7]    code ready                  (4.2s)
✓ Functional     [gpt-5-mini]         pass                         (0.9s)
✓ Security       [claude-sonnet-4-6]  pass                         (1.8s)
✓ Performance    [gpt-5-mini]         pass                         (0.8s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Done  · 2 files written · 1 retry · 18.7s total
  → src/utils.c         (modified)
  → tests/test_utils.c  (created)
  → reports/abc123.md   (run report)
```

### Human Loop in CLI

When an agent escalates, the CLI blocks and prompts:

```
⚠ Security Reviewer needs input (confidence 0.48)
  The memory allocation pattern is ambiguous — should binary_search own
  the buffer, or does the caller? This affects where bounds checks live.

  Your response: _
```

The response is injected back into the agent's context and execution resumes.

---

## Web UI

Built with **FastAPI** (backend) and plain HTML + JavaScript (frontend). Real-time updates delivered via **Server-Sent Events (SSE)** — no polling, no WebSocket complexity.

### Layout

```
┌──────────────────────────────────────────────────────┐
│  MyCoder                              localhost:7433  │
├──────────────┬───────────────────────────────────────┤
│ Jobs         │  add binary_search() to utils.c        │
│              │  job abc123 · C · 18.7s · 1 retry      │
│ ● abc123     │                                        │
│   running    │  ✓ Planner       opus-4-7    3.1s      │
│              │  ✓ Plan Verifier sonnet-4-6  1.2s      │
│ ○ ab9f2      │  ✓ Generator     opus-4-7↑C  9.6s      │
│   done       │  ⚠ Security (1)  sonnet-4-6  2.1s      │
│              │    [MAJOR] Buffer overflow at line 42  │
│ ○ ab8e1      │  ✓ All Reviewers (2)         3.5s      │
│   done       │                                        │
│              │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━    │
│              │  ✓ Done — src/utils.c modified         │
└──────────────┴───────────────────────────────────────┘
```

### Human Loop in Web UI

When escalation occurs, a banner appears in the main panel:

```
┌─────────────────────────────────────────────────────┐
│ ⚠ Agent needs your input                            │
│                                                     │
│ Security Reviewer (confidence 0.48):                │
│ The memory allocation pattern is ambiguous —        │
│ should binary_search own the buffer, or does the    │
│ caller? This affects where bounds checks live.      │
│                                                     │
│ [Reply in terminal]  [View full context]            │
└─────────────────────────────────────────────────────┘
```

The same prompt simultaneously appears in the CLI. The user can respond in either. Once a response is submitted, the banner clears and the pipeline resumes.

---

## SSE Event Protocol

The backend emits events on the `/jobs/{job_id}/stream` endpoint.

```
event: agent_start
data: {"agent": "generator", "model": "claude-opus-4-7", "attempt": 2}

event: agent_done
data: {"agent": "generator", "duration_ms": 4200, "confidence": 0.87}

event: agent_fail
data: {"agent": "security", "issues": [...], "early_exit": false}

event: human_needed
data: {"agent": "security", "confidence": 0.48, "message": "..."}

event: job_done
data: {"files_written": ["src/utils.c", "tests/test_utils.c"], "report": "reports/abc123.md"}
```

Both the Web UI and CLI subscribe to this stream. This keeps the two interfaces in sync without duplicating event logic.
