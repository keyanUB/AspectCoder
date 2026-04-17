# AspectCoder

A local multi-agent coding assistant that plans, generates, and reviews code using LLMs — all from your terminal.

## How it works

AspectCoder runs a DAG pipeline of specialised agents for every task:

```
Task description
      │
      ▼
  Planner ──► PlanVerifier
      │
      ▼
  Generator
      │
      ▼
  Functional reviewer
      │  (parallel)
  Security reviewer ◄── CWE Top 25 / OWASP SCP (embedded locally)
  Performance reviewer
      │
      ▼
  Aggregator ──► DONE / REGEN / REPLAN / HUMAN
      │
      ▼
 Generated files written to project directory
```

Each review cycle either accepts the output, asks the generator to fix issues, replans from scratch, or escalates to you if the problem requires human judgment.

## Features

- **Multi-agent pipeline** — dedicated agents for planning, generation, and three review dimensions
- **Configurable reviewers** — enable only the reviewers you need per run
- **Three security levels** — `basic`, `standard` (CWE Top 25), `strict` (CWE Top 25 + OWASP SCP)
- **Local security knowledge** — CWE Top 25 and OWASP Secure Coding Practices embedded locally; no retrieval needed
- **Prompt caching** — static knowledge blocks are cached server-side for token efficiency
- **Best-effort completion** — accepts output when only minor/non-critical issues remain after max retries
- **Job history** — every run is snapshotted; roll back to any previous version
- **Provider-agnostic** — any model supported by [LiteLLM](https://github.com/BerriAI/litellm) works (Anthropic, OpenAI, …)

## Requirements

- Python 3.11+
- An Anthropic and/or OpenAI API key

## Installation

```bash
git clone https://github.com/keyanguo/AspectCoder.git
cd AspectCoder
pip install -e .
```

## Configuration

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY and/or OPENAI_API_KEY
```

AspectCoder reads `config.yaml` in the working directory. The default config uses:

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

## Usage

### Run a task

```bash
# Inline task description
aspectcoder run "Implement a thread-safe LRU cache in Python with get/put and a pytest suite"

# From a Markdown spec file
aspectcoder run --file demo/python-lru-cache.md
```

### Reviewer options

```bash
# Run only functional and security reviewers (skip performance)
aspectcoder run --file task.md --reviewer functional --reviewer security

# Skip all reviews (generate only)
aspectcoder run --file task.md --reviewer none
```

### Security level

```bash
# basic  — obvious issues only (fastest, cheapest)
aspectcoder run --file task.md --security-level basic

# standard — CWE Top 25 (default)
aspectcoder run --file task.md --security-level standard

# strict  — CWE Top 25 + OWASP Secure Coding Practices
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

## Demo tasks

Three example specs are included in `demo/`:

| File | Language | Task |
|---|---|---|
| `demo/python-lru-cache.md` | Python | LRU cache with O(1) get/put |
| `demo/c-linked-list.md` | C | Doubly-linked list |
| `demo/js-event-emitter.md` | JavaScript | EventEmitter class |
| `demo/python-mirror-pairs.md` | Python | LeetCode 3761 — Mirror Pairs |

```bash
aspectcoder run --file demo/python-lru-cache.md
```

## Output

After a successful run:

- Generated source files are written to the paths specified by the planner (e.g. `src/lru_cache.py`, `tests/test_lru_cache.py`)
- A Markdown report is saved to `reports/<job-id>.md`
- All snapshots are stored under `.aspectcoder/jobs/<job-id>/`

## Development

```bash
pip install -e ".[dev]"
pytest
```

The project is developed with strict TDD (Red → Green → Refactor). All 140+ tests must pass before merging.

## License

MIT — see [LICENSE](LICENSE).
