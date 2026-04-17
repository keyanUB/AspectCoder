# AspectCoder

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![LiteLLM](https://img.shields.io/badge/Powered%20by-LiteLLM-orange.svg)](https://github.com/BerriAI/litellm)

A local multi-agent coding assistant that plans, generates, and peer-reviews code using LLMs — entirely from your terminal.

---

## Why AspectCoder?

LLMs write code fast, but a single prompt-to-code pass has no guardrails: the output may be logically broken, insecure, or slow — and you won't know until you run it.

AspectCoder wraps generation in a structured multi-agent review loop. A dedicated **Planner** designs the approach, a **Generator** writes the code, and three independent reviewers — **Functional**, **Security**, and **Performance** — critique it in parallel. An **Aggregator** decides whether to accept, ask the generator to fix issues, replan from scratch, or escalate to you. The result is code you can trust without manual spot-checking.

---

## How it works

```
  Task description
        │
        ▼
    Planner ◄──────────────────────────────────────┐
        │                                           │
        ▼                                           │
  PlanVerifier ── reject ──► (replan, max 3)       │
        │ approve                                   │
        ▼                                           │
    Generator ◄── retry feedback ──────────────┐   │
        │                                       │   │
        ▼                                       │   │
  ┌─────────────────────────────────────────┐   │   │
  │  Functional reviewer                    │   │   │
  │            │ pass                       │   │   │
  │            ▼                            │   │   │
  │  ┌──────────────────────────────────┐   │   │   │
  │  │  Security reviewer   (parallel)  │   │   │   │
  │  │    ◄── CWE Top 25 / OWASP SCP   │   │   │   │
  │  │  Performance reviewer            │   │   │   │
  │  └──────────────────────────────────┘   │   │   │
  └─────────────────────────────────────────┘   │   │
        │                                       │   │
        ▼                                       │   │
    Aggregator                                  │   │
        ├── REGEN  ──────────────────────────┘   │
        ├── REPLAN ──────────────────────────────┘
        ├── HUMAN  ──► escalate to user
        └── DONE
              │
              ▼
    Generated files + per-attempt snapshots
    written to project directory
```

Each cycle either accepts the output, asks the generator to fix specific issues, replans from scratch, or escalates to you when human judgment is required.

---

## Features

- **Multi-agent pipeline** — dedicated agents for planning, generation, and three orthogonal review dimensions
- **Configurable reviewers** — enable only the reviewers you need per run; skip all with `--reviewer none`
- **Three security levels** — `basic` (fast), `standard` (CWE Top 25), `strict` (CWE Top 25 + OWASP SCP)
- **Local security knowledge** — CWE Top 25 and OWASP Secure Coding Practices are embedded locally; no retrieval calls
- **Prompt caching** — static knowledge blocks are cached server-side, cutting redundant token usage
- **Best-effort completion** — accepts output when only minor issues remain after exhausting retries
- **Job history** — every run is snapshotted; roll back to any previous version instantly
- **Provider-agnostic** — any model supported by [LiteLLM](https://github.com/BerriAI/litellm) works out of the box (Anthropic, OpenAI, …)

---

## Requirements

- Python 3.11+
- An Anthropic and/or OpenAI API key

---

## Installation

```bash
git clone https://github.com/keyanUB/AspectCoder.git
cd AspectCoder
pip install -e .
```

---

## Configuration

Copy the example env file and add your API keys:

```bash
cp .env.example .env
# edit .env — set ANTHROPIC_API_KEY and/or OPENAI_API_KEY
```

AspectCoder reads `config.yaml` from the working directory. The default model assignments are:

| Agent | Model |
|---|---|
| Planner | claude-opus-4-7 |
| Generator | claude-sonnet-4-6 (default), claude-opus-4-7 (C/C++) |
| Plan verifier | claude-sonnet-4-6 |
| Functional reviewer | gpt-5-mini |
| Security reviewer | claude-sonnet-4-6 |
| Performance reviewer | gpt-5-mini |
| Aggregator | claude-haiku-4-5 / claude-sonnet-4-6 |

Edit `config.yaml` to swap in any LiteLLM-supported model.

---

## Usage

### Run a task

```bash
# Inline description
aspectcoder run "Implement a thread-safe LRU cache in Python with get/put and a pytest suite"

# From a Markdown spec file
aspectcoder run --file demo/python-lru-cache.md
```

### Select reviewers

```bash
# Only functional + security (skip performance)
aspectcoder run --file task.md --reviewer functional --reviewer security

# Skip all reviews — generate only
aspectcoder run --file task.md --reviewer none
```

### Set security level

```bash
# basic — obvious issues only (fastest, cheapest)
aspectcoder run --file task.md --security-level basic

# standard — CWE Top 25 (default)
aspectcoder run --file task.md --security-level standard

# strict — CWE Top 25 + OWASP Secure Coding Practices
aspectcoder run --file task.md --security-level strict
```

### Check job status

```bash
aspectcoder status <job-id>
```

### Roll back generated files

```bash
aspectcoder rollback <job-id> --version 1
```

---

## Demo tasks

Four example specs are in `demo/`:

| File | Language | Task |
|---|---|---|
| `demo/python-lru-cache.md` | Python | LRU cache with O(1) get/put |
| `demo/c-linked-list.md` | C | Doubly-linked list |
| `demo/js-event-emitter.md` | JavaScript | EventEmitter class |
| `demo/python-mirror-pairs.md` | Python | LeetCode 3761 — Mirror Pairs |

```bash
aspectcoder run --file demo/python-lru-cache.md
```

---

## Output

After a successful run:

- Generated source files are written to the paths chosen by the planner (e.g. `src/lru_cache.py`, `tests/test_lru_cache.py`)
- A Markdown report is saved to `reports/<job-id>.md`
- All snapshots are stored under `.aspectcoder/jobs/<job-id>/`

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

The project follows strict TDD (Red → Green → Refactor). All 140+ tests must pass before merging.

---

## License

MIT — see [LICENSE](LICENSE).
