# MyCoder — System Overview

## What It Is

MyCoder is a local, single-user agentic coding system where multiple specialised AI agents collaborate to plan, generate, and review code. A user describes a task in natural language; a pipeline of agents produces working, reviewed code.

It handles both:
- **New code generation** — implementing features, functions, or scripts from scratch
- **Existing code improvement** — bug fixes, refactoring, security hardening

## Supported Languages

Python, C, C++, JavaScript

## Architecture

Four layers, each with a clear responsibility:

```
┌──────────────────────────────────────────────┐
│              User Interfaces                 │
│        CLI (Typer)  │  Web UI (FastAPI+SSE)  │
└──────────────────────────────────────────────┘
                      │
┌──────────────────────────────────────────────┐
│             Core Coordination                │
│  Task Manager │ DAG Orchestrator │ Human Loop │
└──────────────────────────────────────────────┘
                      │
┌──────────────────────────────────────────────┐
│                 Agent Pool                   │
│  Planner │ Verifier │ Generator │ Reviewers  │
│                  Aggregator                  │
└──────────────────────────────────────────────┘
                      │
┌──────────────────────────────────────────────┐
│               Support Layer                  │
│  LLM Provider (LiteLLM) │ Context Manager   │
│  Output Manager         │ Storage           │
└──────────────────────────────────────────────┘
```

## Design Principles

**Provider-agnostic LLM layer.** All agents talk to LiteLLM, which routes to Anthropic, OpenAI, or local models. Swapping a model means changing one line in `config.yaml`, not touching agent code.

**Model tiering.** Different agents use different models matched to task complexity and cost sensitivity. See `llm-config.md`.

**Sequential review with early exit.** Functional correctness is checked first. Security and Performance reviewers only run if Functional passes, saving tokens on failing generations.

**Adaptive human escalation.** Agents emit a confidence score with every output. When confidence drops below 0.5, or when retry budgets are exhausted, the Human Loop is triggered. Agents can also explicitly request human input.

**Versioned job state.** Every plan and code version produced during a job is persisted to disk. Users can inspect or roll back to any prior version. See `storage.md`.

**Routing logic in code, not prompts.** The Aggregator's routing decisions (regen vs replan vs escalate) are implemented as Python conditionals, not delegated to an LLM. LLMs are used only for synthesis and generation tasks.

## Related Design Documents

| File | Contents |
|---|---|
| `pipeline-flow.md` | End-to-end agent execution, routing, retry logic |
| `agents.md` | Each agent's role, inputs, outputs |
| `data-models.md` | Pydantic schemas for all inter-agent data |
| `llm-config.md` | Model assignments, LiteLLM setup, prompt caching |
| `interfaces.md` | CLI commands, Web UI, SSE protocol, Human Loop |
| `storage.md` | Job versioning, snapshot format, rollback |
