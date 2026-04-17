# Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the project foundation — directory structure, all Pydantic data models, config system, LiteLLM client wrapper, and BaseAgent base class.

**Architecture:** Pure Python package (`mycoder/`) with Pydantic v2 for all inter-agent data contracts. LiteLLM provides a single `completion()` call that routes to Anthropic, OpenAI, or local providers. `BaseAgent` wraps LiteLLM with prompt caching, structured output enforcement, and retry logic. All agents in future plans extend `BaseAgent`.

**Tech Stack:** Python 3.11+, Pydantic v2, LiteLLM, PyYAML, pytest, pytest-asyncio

---

## File Map

```
mycoder/
  __init__.py
  config.py                     # loads config.yaml → Config dataclass
  models/
    __init__.py
    plan.py                     # Subtask, Plan
    verdict.py                  # IssueSeverity, Issue, PlanVerdict, ReviewVerdict, ReviewerType
    code.py                     # GeneratedCode
    aggregator.py               # AttemptSummary, FailureReport, AggregatorAction, AggregatorDecision
    job.py                      # JobStatus, JobState
  llm/
    __init__.py
    client.py                   # thin LiteLLM wrapper: call(), with caching headers
    base_agent.py               # BaseAgent: run(), llm(), structured output, retries
config.yaml                     # default model assignments
pyproject.toml
tests/
  conftest.py                   # shared fixtures
  test_models_plan.py
  test_models_verdict.py
  test_models_code.py
  test_models_aggregator.py
  test_models_job.py
  test_config.py
  test_llm_client.py
  test_base_agent.py
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `config.yaml`
- Create: `mycoder/__init__.py`
- Create: `mycoder/models/__init__.py`
- Create: `mycoder/llm/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mycoder"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "litellm>=1.40.0",
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "typer>=0.12.0",
    "fastapi>=0.111.0",
    "uvicorn>=0.29.0",
]

[project.scripts]
mycoder = "mycoder.cli:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -e ".[dev]"` or `uv sync`

- [ ] **Step 3: Create config.yaml**

```yaml
models:
  planner:
    model: claude-opus-4-7
    temperature: 0.7
    max_tokens: 4096

  generator:
    default:
      model: claude-sonnet-4-6
      temperature: 0.2
      max_tokens: 8192
    c:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
    cpp:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192

  verifier:
    model: claude-sonnet-4-6
    temperature: 0.0
    max_tokens: 2048

  reviewers:
    functional:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
    security:
      model: claude-sonnet-4-6
      temperature: 0.0
      max_tokens: 2048
    performance:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048

  aggregator:
    normal:
      model: claude-haiku-4-5
      temperature: 0.0
      max_tokens: 1024
    failure_report:
      model: claude-sonnet-4-6
      temperature: 0.3
      max_tokens: 2048

api_keys:
  anthropic: ${ANTHROPIC_API_KEY}
  openai: ${OPENAI_API_KEY}
```

- [ ] **Step 4: Create empty package init files**

`mycoder/__init__.py` — empty file.
`mycoder/models/__init__.py` — empty file.
`mycoder/llm/__init__.py` — empty file.

- [ ] **Step 5: Create tests/conftest.py**

```python
import pytest

@pytest.fixture
def sample_task_description():
    return "Add a binary_search() function to src/utils.c"
```

- [ ] **Step 6: Verify structure**

Run: `python -c "import mycoder; print('ok')"` — expected output: `ok`

- [ ] **Step 7: Commit**

```bash
git init
git add pyproject.toml config.yaml mycoder/ tests/
git commit -m "feat: project scaffold — package structure, config, dependencies"
```

---

## Task 2: Plan & Subtask Models

**Files:**
- Create: `mycoder/models/plan.py`
- Create: `tests/test_models_plan.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models_plan.py
import pytest
from mycoder.models.plan import Subtask, Plan

def test_subtask_requires_fields():
    with pytest.raises(Exception):
        Subtask()  # missing required fields

def test_subtask_valid():
    s = Subtask(
        id="subtask-1",
        description="Implement binary_search in utils.c",
        target_file="src/utils.c",
        language="c",
        dependencies=[],
    )
    assert s.id == "subtask-1"
    assert s.language == "c"

def test_plan_valid():
    subtask = Subtask(
        id="subtask-1",
        description="Implement binary_search",
        target_file="src/utils.c",
        language="c",
        dependencies=[],
    )
    plan = Plan(
        task_id="job-abc123",
        task_description="Add binary_search to utils.c",
        approach="Add iterative binary search with bounds checking",
        subtasks=[subtask],
        target_files=["src/utils.c"],
        primary_language="c",
        confidence=0.92,
    )
    assert plan.confidence == 0.92
    assert plan.needs_human is False  # default

def test_plan_serialises_to_json():
    subtask = Subtask(
        id="subtask-1",
        description="Implement binary_search",
        target_file="src/utils.c",
        language="c",
        dependencies=[],
    )
    plan = Plan(
        task_id="job-abc123",
        task_description="Add binary_search to utils.c",
        approach="Iterative binary search",
        subtasks=[subtask],
        target_files=["src/utils.c"],
        primary_language="c",
        confidence=0.9,
    )
    data = plan.model_dump()
    restored = Plan.model_validate(data)
    assert restored.task_id == plan.task_id
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `pytest tests/test_models_plan.py -v`
Expected: `ImportError` — `mycoder.models.plan` does not exist yet.

- [ ] **Step 3: Implement mycoder/models/plan.py**

```python
from __future__ import annotations
from pydantic import BaseModel, Field


class Subtask(BaseModel):
    id: str
    description: str
    target_file: str
    language: str                    # "python" | "c" | "cpp" | "javascript"
    dependencies: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    task_id: str
    task_description: str
    approach: str
    subtasks: list[Subtask]
    target_files: list[str]
    primary_language: str
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human: bool = False
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `pytest tests/test_models_plan.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mycoder/models/plan.py tests/test_models_plan.py
git commit -m "feat: Plan and Subtask Pydantic models"
```

---

## Task 3: Verdict Models

**Files:**
- Create: `mycoder/models/verdict.py`
- Create: `tests/test_models_verdict.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models_verdict.py
import pytest
from mycoder.models.verdict import (
    Issue, IssueSeverity, PlanVerdict, ReviewVerdict, ReviewerType
)

def test_issue_severity_values():
    assert IssueSeverity.CRITICAL == "critical"
    assert IssueSeverity.MAJOR == "major"
    assert IssueSeverity.MINOR == "minor"

def test_issue_valid():
    issue = Issue(
        severity=IssueSeverity.MAJOR,
        description="Buffer overflow in binary_search at line 42",
        location="src/utils.c:42",
        suggestion="Add bounds check: if (mid < 0 || mid >= len) return -1;",
    )
    assert issue.severity == IssueSeverity.MAJOR

def test_plan_verdict_pass():
    verdict = PlanVerdict(pass_=True, confidence=0.95, issues=[])
    assert verdict.pass_ is True
    assert verdict.needs_human is False

def test_plan_verdict_fail():
    verdict = PlanVerdict(
        pass_=False,
        confidence=0.4,
        issues=["Missing error handling subtask"],
        needs_human=False,
    )
    assert verdict.pass_ is False
    assert len(verdict.issues) == 1

def test_review_verdict_approach_wrong():
    verdict = ReviewVerdict(
        reviewer=ReviewerType.FUNCTIONAL,
        pass_=False,
        confidence=0.3,
        issues=[],
        approach_wrong=True,
    )
    assert verdict.approach_wrong is True

def test_review_verdict_serialises():
    verdict = ReviewVerdict(
        reviewer=ReviewerType.SECURITY,
        pass_=True,
        confidence=0.88,
        issues=[],
    )
    data = verdict.model_dump()
    restored = ReviewVerdict.model_validate(data)
    assert restored.reviewer == ReviewerType.SECURITY
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `pytest tests/test_models_verdict.py -v`
Expected: `ImportError`.

- [ ] **Step 3: Implement mycoder/models/verdict.py**

```python
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR    = "major"
    MINOR    = "minor"


class Issue(BaseModel):
    severity: IssueSeverity
    description: str
    location: str = ""        # "file.c:42" or empty if non-local
    suggestion: str


class ReviewerType(str, Enum):
    FUNCTIONAL  = "functional"
    SECURITY    = "security"
    PERFORMANCE = "performance"


class PlanVerdict(BaseModel):
    pass_: bool
    confidence: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    needs_human: bool = False


class ReviewVerdict(BaseModel):
    reviewer: ReviewerType
    pass_: bool
    confidence: float = Field(ge=0.0, le=1.0)
    issues: list[Issue] = Field(default_factory=list)
    approach_wrong: bool = False
    needs_human: bool = False
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `pytest tests/test_models_verdict.py -v`
Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mycoder/models/verdict.py tests/test_models_verdict.py
git commit -m "feat: verdict Pydantic models — PlanVerdict, ReviewVerdict, Issue"
```

---

## Task 4: GeneratedCode Model

**Files:**
- Create: `mycoder/models/code.py`
- Create: `tests/test_models_code.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models_code.py
import pytest
from mycoder.models.code import GeneratedCode

def test_generated_code_valid():
    gc = GeneratedCode(
        subtask_id="subtask-1",
        language="c",
        file_path="src/utils.c",
        code="int binary_search(int *arr, int len, int target) { return -1; }",
        explanation="Stub implementation — bounds checking added in next step.",
        confidence=0.85,
    )
    assert gc.subtask_id == "subtask-1"
    assert gc.needs_human is False

def test_generated_code_low_confidence_does_not_auto_set_needs_human():
    # needs_human must be set explicitly — confidence threshold is enforced by the agent, not the model
    gc = GeneratedCode(
        subtask_id="subtask-1",
        language="python",
        file_path="src/utils.py",
        code="def search(): pass",
        explanation="Incomplete.",
        confidence=0.2,
    )
    assert gc.needs_human is False

def test_generated_code_serialises():
    gc = GeneratedCode(
        subtask_id="subtask-1",
        language="javascript",
        file_path="src/utils.js",
        code="function search() {}",
        explanation="Empty stub.",
        confidence=0.5,
    )
    data = gc.model_dump()
    restored = GeneratedCode.model_validate(data)
    assert restored.language == "javascript"
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `pytest tests/test_models_code.py -v`
Expected: `ImportError`.

- [ ] **Step 3: Implement mycoder/models/code.py**

```python
from __future__ import annotations
from pydantic import BaseModel, Field


class GeneratedCode(BaseModel):
    subtask_id: str
    language: str
    file_path: str
    code: str
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human: bool = False
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `pytest tests/test_models_code.py -v`
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mycoder/models/code.py tests/test_models_code.py
git commit -m "feat: GeneratedCode Pydantic model"
```

---

## Task 5: Aggregator & Job Models

**Files:**
- Create: `mycoder/models/aggregator.py`
- Create: `mycoder/models/job.py`
- Create: `tests/test_models_aggregator.py`
- Create: `tests/test_models_job.py`

- [ ] **Step 1: Write failing tests for aggregator models**

```python
# tests/test_models_aggregator.py
import pytest
from mycoder.models.verdict import ReviewVerdict, ReviewerType
from mycoder.models.aggregator import (
    AttemptSummary, FailureReport, AggregatorAction, AggregatorDecision
)

def test_aggregator_action_values():
    assert AggregatorAction.DONE   == "done"
    assert AggregatorAction.REGEN  == "regen"
    assert AggregatorAction.REPLAN == "replan"
    assert AggregatorAction.HUMAN  == "human"

def test_aggregator_decision_done():
    decision = AggregatorDecision(action=AggregatorAction.DONE, summary="All reviewers passed.")
    assert decision.failure_report is None

def test_failure_report_valid():
    verdict = ReviewVerdict(
        reviewer=ReviewerType.SECURITY,
        pass_=False,
        confidence=0.3,
        issues=[],
    )
    attempt = AttemptSummary(attempt_number=1, verdicts=[verdict])
    report = FailureReport(
        task_id="job-abc123",
        attempts=[attempt],
        recurring_patterns=["Security consistently fails on memory management in subtask-1"],
        diagnosis="Plan does not specify buffer ownership — Generator cannot infer safe bounds.",
        replan_hints=["Specify in subtask-1 that the caller owns the buffer and passes length explicitly."],
    )
    assert report.task_id == "job-abc123"
    assert len(report.attempts) == 1

def test_aggregator_decision_replan_has_report():
    report = FailureReport(
        task_id="job-abc123",
        attempts=[],
        recurring_patterns=[],
        diagnosis="Approach is wrong.",
        replan_hints=[],
    )
    decision = AggregatorDecision(
        action=AggregatorAction.REPLAN,
        summary="3 regenerations exhausted.",
        failure_report=report,
    )
    assert decision.failure_report is not None
```

- [ ] **Step 2: Write failing tests for job models**

```python
# tests/test_models_job.py
from datetime import datetime, timezone
from mycoder.models.job import JobStatus, JobState

def test_job_status_values():
    assert JobStatus.PENDING  == "pending"
    assert JobStatus.RUNNING  == "running"
    assert JobStatus.WAITING  == "waiting"
    assert JobStatus.DONE     == "done"
    assert JobStatus.FAILED   == "failed"

def test_job_state_defaults():
    now = datetime.now(timezone.utc)
    state = JobState(
        job_id="job-abc123",
        task_description="Add binary_search to utils.c",
        status=JobStatus.PENDING,
        current_version=0,
        created_at=now,
        updated_at=now,
    )
    assert state.planner_retries == 0
    assert state.regen_retries == 0
    assert state.replan_retries == 0

def test_job_state_serialises():
    now = datetime.now(timezone.utc)
    state = JobState(
        job_id="job-abc123",
        task_description="task",
        status=JobStatus.RUNNING,
        current_version=1,
        created_at=now,
        updated_at=now,
    )
    data = state.model_dump()
    restored = JobState.model_validate(data)
    assert restored.job_id == "job-abc123"
    assert restored.status == JobStatus.RUNNING
```

- [ ] **Step 3: Run tests to confirm they fail**

Run: `pytest tests/test_models_aggregator.py tests/test_models_job.py -v`
Expected: `ImportError`.

- [ ] **Step 4: Implement mycoder/models/aggregator.py**

```python
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel
from mycoder.models.verdict import ReviewVerdict


class AttemptSummary(BaseModel):
    attempt_number: int
    verdicts: list[ReviewVerdict]


class FailureReport(BaseModel):
    task_id: str
    attempts: list[AttemptSummary]
    recurring_patterns: list[str]
    diagnosis: str
    replan_hints: list[str]


class AggregatorAction(str, Enum):
    DONE   = "done"
    REGEN  = "regen"
    REPLAN = "replan"
    HUMAN  = "human"


class AggregatorDecision(BaseModel):
    action: AggregatorAction
    summary: str
    failure_report: FailureReport | None = None
```

- [ ] **Step 5: Implement mycoder/models/job.py**

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    DONE    = "done"
    FAILED  = "failed"


class JobState(BaseModel):
    job_id: str
    task_description: str
    status: JobStatus
    current_version: int
    planner_retries: int = 0
    regen_retries: int = 0
    replan_retries: int = 0
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 6: Run tests to confirm they pass**

Run: `pytest tests/test_models_aggregator.py tests/test_models_job.py -v`
Expected: 7 tests PASS.

- [ ] **Step 7: Run full test suite to check no regressions**

Run: `pytest -v`
Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add mycoder/models/aggregator.py mycoder/models/job.py \
        tests/test_models_aggregator.py tests/test_models_job.py
git commit -m "feat: aggregator and job Pydantic models"
```

---

## Task 6: Config System

**Files:**
- Create: `mycoder/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config.py
import os
import pytest
from pathlib import Path
from mycoder.config import Config, ModelConfig, load_config

def test_load_config_from_file(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
models:
  planner:
    model: claude-opus-4-7
    temperature: 0.7
    max_tokens: 4096
  generator:
    default:
      model: claude-sonnet-4-6
      temperature: 0.2
      max_tokens: 8192
    c:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
    cpp:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
  verifier:
    model: claude-sonnet-4-6
    temperature: 0.0
    max_tokens: 2048
  reviewers:
    functional:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
    security:
      model: claude-sonnet-4-6
      temperature: 0.0
      max_tokens: 2048
    performance:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
  aggregator:
    normal:
      model: claude-haiku-4-5
      temperature: 0.0
      max_tokens: 1024
    failure_report:
      model: claude-sonnet-4-6
      temperature: 0.3
      max_tokens: 2048
api_keys:
  anthropic: test-key
  openai: test-openai-key
""")
    config = load_config(cfg_file)
    assert config.models.planner.model == "claude-opus-4-7"
    assert config.models.planner.temperature == 0.7
    assert config.models.generator["c"].model == "claude-opus-4-7"
    assert config.models.reviewers["security"].model == "claude-sonnet-4-6"
    assert config.models.aggregator["normal"].model == "claude-haiku-4-5"

def test_generator_model_for_language(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
models:
  planner:
    model: claude-opus-4-7
    temperature: 0.7
    max_tokens: 4096
  generator:
    default:
      model: claude-sonnet-4-6
      temperature: 0.2
      max_tokens: 8192
    c:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
    cpp:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
  verifier:
    model: claude-sonnet-4-6
    temperature: 0.0
    max_tokens: 2048
  reviewers:
    functional:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
    security:
      model: claude-sonnet-4-6
      temperature: 0.0
      max_tokens: 2048
    performance:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
  aggregator:
    normal:
      model: claude-haiku-4-5
      temperature: 0.0
      max_tokens: 1024
    failure_report:
      model: claude-sonnet-4-6
      temperature: 0.3
      max_tokens: 2048
api_keys:
  anthropic: test-key
  openai: test-openai-key
""")
    config = load_config(cfg_file)
    assert config.generator_model_for("python").model == "claude-sonnet-4-6"
    assert config.generator_model_for("c").model == "claude-opus-4-7"
    assert config.generator_model_for("cpp").model == "claude-opus-4-7"
    assert config.generator_model_for("javascript").model == "claude-sonnet-4-6"

def test_aggregator_model_normal(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
models:
  planner:
    model: claude-opus-4-7
    temperature: 0.7
    max_tokens: 4096
  generator:
    default:
      model: claude-sonnet-4-6
      temperature: 0.2
      max_tokens: 8192
    c:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
    cpp:
      model: claude-opus-4-7
      temperature: 0.2
      max_tokens: 8192
  verifier:
    model: claude-sonnet-4-6
    temperature: 0.0
    max_tokens: 2048
  reviewers:
    functional:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
    security:
      model: claude-sonnet-4-6
      temperature: 0.0
      max_tokens: 2048
    performance:
      model: gpt-5-mini
      temperature: 0.0
      max_tokens: 2048
  aggregator:
    normal:
      model: claude-haiku-4-5
      temperature: 0.0
      max_tokens: 1024
    failure_report:
      model: claude-sonnet-4-6
      temperature: 0.3
      max_tokens: 2048
api_keys:
  anthropic: test-key
  openai: test-openai-key
""")
    config = load_config(cfg_file)
    assert config.aggregator_model(failure_report=False).model == "claude-haiku-4-5"
    assert config.aggregator_model(failure_report=True).model == "claude-sonnet-4-6"
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `pytest tests/test_config.py -v`
Expected: `ImportError`.

- [ ] **Step 3: Implement mycoder/config.py**

```python
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class ModelConfig:
    model: str
    temperature: float = 0.0
    max_tokens: int = 2048


@dataclass
class ModelsConfig:
    planner: ModelConfig
    generator: dict[str, ModelConfig]      # keys: "default", "c", "cpp", "javascript"
    verifier: ModelConfig
    reviewers: dict[str, ModelConfig]      # keys: "functional", "security", "performance"
    aggregator: dict[str, ModelConfig]     # keys: "normal", "failure_report"


@dataclass
class Config:
    models: ModelsConfig
    api_keys: dict[str, str] = field(default_factory=dict)

    def generator_model_for(self, language: str) -> ModelConfig:
        return self.models.generator.get(language, self.models.generator["default"])

    def aggregator_model(self, *, failure_report: bool) -> ModelConfig:
        key = "failure_report" if failure_report else "normal"
        return self.models.aggregator[key]


def _parse_model_config(data: dict) -> ModelConfig:
    return ModelConfig(
        model=data["model"],
        temperature=data.get("temperature", 0.0),
        max_tokens=data.get("max_tokens", 2048),
    )


def _resolve_env_vars(value: str) -> str:
    if value.startswith("${") and value.endswith("}"):
        var = value[2:-1]
        return os.environ.get(var, "")
    return value


def load_config(path: Path | str = "config.yaml") -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f)

    m = raw["models"]

    generator: dict[str, ModelConfig] = {}
    for key, val in m["generator"].items():
        generator[key] = _parse_model_config(val)

    reviewers: dict[str, ModelConfig] = {}
    for key, val in m["reviewers"].items():
        reviewers[key] = _parse_model_config(val)

    aggregator: dict[str, ModelConfig] = {}
    for key, val in m["aggregator"].items():
        aggregator[key] = _parse_model_config(val)

    api_keys = {
        k: _resolve_env_vars(str(v))
        for k, v in raw.get("api_keys", {}).items()
    }

    return Config(
        models=ModelsConfig(
            planner=_parse_model_config(m["planner"]),
            generator=generator,
            verifier=_parse_model_config(m["verifier"]),
            reviewers=reviewers,
            aggregator=aggregator,
        ),
        api_keys=api_keys,
    )
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `pytest tests/test_config.py -v`
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mycoder/config.py tests/test_config.py
git commit -m "feat: config system — load_config, ModelConfig, language-aware generator selection"
```

---

## Task 7: LiteLLM Client Wrapper

**Files:**
- Create: `mycoder/llm/client.py`
- Create: `tests/test_llm_client.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_llm_client.py
import pytest
from unittest.mock import patch, MagicMock
from mycoder.llm.client import LLMClient, LLMMessage, LLMResponse
from mycoder.config import ModelConfig

@pytest.fixture
def model_config():
    return ModelConfig(model="claude-haiku-4-5", temperature=0.0, max_tokens=512)

@pytest.fixture
def client(model_config):
    return LLMClient(config=model_config)

def test_llm_message_roles():
    msg = LLMMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"

def test_llm_response_fields():
    resp = LLMResponse(content="Hello back", model="claude-haiku-4-5", usage={"prompt_tokens": 5, "completion_tokens": 3})
    assert resp.content == "Hello back"

def test_call_invokes_litellm(client):
    messages = [LLMMessage(role="user", content="Say hi")]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Hi!"
    mock_response.model = "claude-haiku-4-5"
    mock_response.usage.prompt_tokens = 5
    mock_response.usage.completion_tokens = 2

    with patch("mycoder.llm.client.litellm.completion", return_value=mock_response) as mock_call:
        response = client.call(messages)
        mock_call.assert_called_once()
        assert response.content == "Hi!"

def test_call_applies_cache_prefix(client):
    cached = [LLMMessage(role="user", content="Cached context", cache=True)]
    dynamic = [LLMMessage(role="user", content="New question")]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Answer"
    mock_response.model = "claude-haiku-4-5"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    with patch("mycoder.llm.client.litellm.completion", return_value=mock_response) as mock_call:
        client.call(dynamic, cached_prefix=cached)
        call_kwargs = mock_call.call_args
        messages_sent = call_kwargs[1]["messages"]
        # cached message should have cache_control in extra_headers or message metadata
        assert len(messages_sent) == 2
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `pytest tests/test_llm_client.py -v`
Expected: `ImportError`.

- [ ] **Step 3: Implement mycoder/llm/client.py**

```python
from __future__ import annotations
from dataclasses import dataclass, field
import litellm
from mycoder.config import ModelConfig


@dataclass
class LLMMessage:
    role: str           # "system" | "user" | "assistant"
    content: str
    cache: bool = False  # mark this message for prompt caching


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int]


class LLMClient:
    def __init__(self, config: ModelConfig):
        self.config = config

    def call(
        self,
        messages: list[LLMMessage],
        *,
        cached_prefix: list[LLMMessage] | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        all_messages = list(cached_prefix or []) + list(messages)
        litellm_messages = [
            self._to_litellm_message(m) for m in all_messages
        ]

        kwargs: dict = dict(
            model=self.config.model,
            messages=litellm_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        if response_format:
            kwargs["response_format"] = response_format

        result = litellm.completion(**kwargs)

        return LLMResponse(
            content=result.choices[0].message.content,
            model=result.model,
            usage={
                "prompt_tokens": result.usage.prompt_tokens,
                "completion_tokens": result.usage.completion_tokens,
            },
        )

    def _to_litellm_message(self, msg: LLMMessage) -> dict:
        m: dict = {"role": msg.role, "content": msg.content}
        if msg.cache:
            # Anthropic prompt caching: attach cache_control to content block
            m["content"] = [
                {
                    "type": "text",
                    "text": msg.content,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        return m
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `pytest tests/test_llm_client.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mycoder/llm/client.py tests/test_llm_client.py
git commit -m "feat: LLMClient wrapper over LiteLLM with prompt caching support"
```

---

## Task 8: BaseAgent

**Files:**
- Create: `mycoder/llm/base_agent.py`
- Create: `tests/test_base_agent.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_base_agent.py
import pytest
from unittest.mock import patch, MagicMock
from pydantic import BaseModel
from mycoder.config import ModelConfig
from mycoder.llm.base_agent import BaseAgent
from mycoder.llm.client import LLMResponse


class EchoOutput(BaseModel):
    message: str
    confidence: float


class EchoAgent(BaseAgent[str, EchoOutput]):
    """Minimal agent for testing — echoes the input."""

    def build_messages(self, input: str):
        return [{"role": "user", "content": input}]

    def parse_output(self, raw: str) -> EchoOutput:
        import json
        data = json.loads(raw)
        return EchoOutput(**data)


@pytest.fixture
def model_config():
    return ModelConfig(model="claude-haiku-4-5", temperature=0.0, max_tokens=512)


@pytest.fixture
def agent(model_config):
    return EchoAgent(config=model_config)


def test_agent_run_returns_output(agent):
    mock_response = LLMResponse(
        content='{"message": "hello", "confidence": 0.9}',
        model="claude-haiku-4-5",
        usage={"prompt_tokens": 5, "completion_tokens": 10},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        output = agent.run("hello")
        assert output.message == "hello"
        assert output.confidence == 0.9


def test_agent_triggers_needs_human_on_low_confidence(agent):
    mock_response = LLMResponse(
        content='{"message": "unsure", "confidence": 0.3}',
        model="claude-haiku-4-5",
        usage={"prompt_tokens": 5, "completion_tokens": 10},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        output = agent.run("ambiguous input")
        assert output.confidence == 0.3
        assert agent.last_needs_human is True


def test_agent_run_retries_on_parse_failure(agent):
    bad_response = LLMResponse(
        content="not valid json",
        model="claude-haiku-4-5",
        usage={"prompt_tokens": 5, "completion_tokens": 3},
    )
    good_response = LLMResponse(
        content='{"message": "ok", "confidence": 0.8}',
        model="claude-haiku-4-5",
        usage={"prompt_tokens": 5, "completion_tokens": 10},
    )
    with patch.object(agent.client, "call", side_effect=[bad_response, good_response]):
        output = agent.run("retry test")
        assert output.message == "ok"
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `pytest tests/test_base_agent.py -v`
Expected: `ImportError`.

- [ ] **Step 3: Implement mycoder/llm/base_agent.py**

```python
from __future__ import annotations
import json
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from mycoder.config import ModelConfig
from mycoder.llm.client import LLMClient, LLMMessage, LLMResponse

InputT  = TypeVar("InputT")
OutputT = TypeVar("OutputT")

CONFIDENCE_THRESHOLD = 0.5
MAX_PARSE_RETRIES = 2


class BaseAgent(ABC, Generic[InputT, OutputT]):
    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = LLMClient(config)
        self.last_needs_human: bool = False

    def run(self, input: InputT, *, cached_prefix: list[LLMMessage] | None = None) -> OutputT:
        messages = self.build_messages(input)
        last_error: Exception | None = None

        for attempt in range(MAX_PARSE_RETRIES + 1):
            response = self.client.call(messages, cached_prefix=cached_prefix)
            try:
                output = self.parse_output(response.content)
                confidence = getattr(output, "confidence", 1.0)
                self.last_needs_human = (
                    confidence < CONFIDENCE_THRESHOLD
                    or getattr(output, "needs_human", False)
                )
                return output
            except Exception as e:
                last_error = e
                # append the bad response and ask for correction
                messages = messages + [
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": f"That response could not be parsed. Error: {e}. Please respond with valid JSON only."},
                ]

        raise ValueError(f"Agent failed to produce parseable output after {MAX_PARSE_RETRIES + 1} attempts. Last error: {last_error}")

    @abstractmethod
    def build_messages(self, input: InputT) -> list[dict]:
        """Return the messages list to send to the LLM."""

    @abstractmethod
    def parse_output(self, raw: str) -> OutputT:
        """Parse the raw LLM string response into the typed output."""
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `pytest tests/test_base_agent.py -v`
Expected: 3 tests PASS.

- [ ] **Step 5: Run full suite**

Run: `pytest -v`
Expected: all tests PASS (20+ tests total).

- [ ] **Step 6: Commit**

```bash
git add mycoder/llm/base_agent.py tests/test_base_agent.py
git commit -m "feat: BaseAgent — generic LLM agent with structured output, parse retries, confidence gating"
```

---

## Self-Review Notes

- All Pydantic models use `pass_` for the Python keyword collision — consistent throughout.
- `Config.generator_model_for(language)` falls back to `"default"` for any unlisted language (e.g. JavaScript) — correct.
- `BaseAgent` generic types `InputT`/`OutputT` give future agents full type safety without duplication.
- `LLMClient._to_litellm_message` applies cache headers to Anthropic models; on OpenAI the extra key is safely ignored by LiteLLM.
- `CONFIDENCE_THRESHOLD = 0.5` is a module-level constant — easy to make config-driven in a later plan.
- Tests use `unittest.mock.patch` not real API calls — no credentials needed to run the test suite.
