# Web UI — Future Implementation

Design spec: `docs/design/interfaces.md` (Web UI section)

## What to build

- **FastAPI backend** at `mycoder/web/app.py`
  - `GET /jobs` — list all jobs with status
  - `GET /jobs/{job_id}` — job detail (state.json)
  - `GET /jobs/{job_id}/stream` — SSE stream of agent events
  - `POST /jobs` — start a new job (same as `mycoder run`)
  - `POST /jobs/{job_id}/human` — submit human-loop response

- **SSE event protocol** (emit from Orchestrator via a callback/event bus)
  - `agent_start` — `{"agent": "generator", "model": "...", "attempt": 2}`
  - `agent_done` — `{"agent": "generator", "duration_ms": 4200, "confidence": 0.87}`
  - `agent_fail` — `{"agent": "security", "issues": [...], "early_exit": false}`
  - `human_needed` — `{"agent": "security", "confidence": 0.48, "message": "..."}`
  - `job_done` — `{"files_written": [...], "report": "reports/abc123.md"}`

- **Plain HTML + JS frontend** at `mycoder/web/static/`
  - Job list sidebar (left panel)
  - Live agent progress panel (right panel, subscribes to SSE stream)
  - Human-loop banner when `human_needed` fires
  - `mycoder ui` CLI command starts server + opens browser

## Prerequisites before starting

1. Add an **event bus / callback** to `Orchestrator` so the Web UI can receive real-time progress
   - The CLI currently only gets the final `OrchestratorResult` — SSE needs per-agent events
   - Suggested: `on_event: Callable[[str, dict], None] | None = None` param on `Orchestrator.run()`
2. Implement **human-loop resume** — `mycoder resume [job-id]` and `POST /jobs/{job_id}/human`
3. Wire `mycoder/web/app.py` into `mycoder/cli/__init__.py` as `mycoder ui`

## Entry point

`mycoder ui` → `uvicorn mycoder.web.app:app --host 0.0.0.0 --port 7433 --reload`
