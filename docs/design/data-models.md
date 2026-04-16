# Data Models

All inter-agent data is defined as Pydantic models. LiteLLM enforces structured JSON output against these schemas — no prompt-parsing fragility.

---

## Plan

Produced by the Planner. Consumed by Plan Verifier and Generator.

```python
class Subtask(BaseModel):
    id: str                        # e.g. "subtask-1"
    description: str
    target_file: str               # e.g. "src/utils.c"
    language: str                  # "python" | "c" | "cpp" | "javascript"
    dependencies: list[str]        # other subtask IDs that must complete first

class Plan(BaseModel):
    task_id: str
    task_description: str
    approach: str                  # high-level strategy in plain English
    subtasks: list[Subtask]
    target_files: list[str]        # all files that will be modified or created
    primary_language: str
    confidence: float              # 0.0–1.0
    needs_human: bool = False
```

---

## PlanVerdict

Produced by the Plan Verifier. Consumed by the DAG Orchestrator.

```python
class PlanVerdict(BaseModel):
    pass_: bool
    confidence: float
    issues: list[str]              # plain English descriptions of problems
    needs_human: bool = False
```

---

## GeneratedCode

Produced by the Generator. One instance per subtask.

```python
class GeneratedCode(BaseModel):
    subtask_id: str
    language: str
    file_path: str
    code: str
    explanation: str               # brief rationale for implementation choices
    confidence: float
    needs_human: bool = False
```

---

## Issue

Embedded in ReviewVerdict. Represents a single finding.

```python
class IssueSeverity(str, Enum):
    CRITICAL = "critical"          # must fix before ship
    MAJOR    = "major"             # should fix
    MINOR    = "minor"             # nice to fix

class Issue(BaseModel):
    severity: IssueSeverity
    description: str
    location: str                  # "file.c:42" or "" if non-local
    suggestion: str                # concrete fix recommendation
```

---

## ReviewVerdict

Produced by each Reviewer agent. Consumed by the Aggregator.

```python
class ReviewerType(str, Enum):
    FUNCTIONAL  = "functional"
    SECURITY    = "security"
    PERFORMANCE = "performance"

class ReviewVerdict(BaseModel):
    reviewer: ReviewerType
    pass_: bool
    confidence: float
    issues: list[Issue]
    approach_wrong: bool = False   # true = replan needed, not just regenerate
    needs_human: bool = False
```

---

## FailureReport

Produced by the Aggregator (Sonnet path) when 3 regeneration cycles are exhausted.
Consumed by the Planner to inform a replan.

```python
class AttemptSummary(BaseModel):
    attempt_number: int            # 1, 2, or 3
    verdicts: list[ReviewVerdict]

class FailureReport(BaseModel):
    task_id: str
    attempts: list[AttemptSummary]
    recurring_patterns: list[str]  # e.g. "security fails on memory mgmt in subtask-2"
    diagnosis: str                 # plain English root cause hypothesis
    replan_hints: list[str]        # specific suggestions for the Planner
```

---

## AggregatorDecision

Produced by the Aggregator. Consumed by the DAG Orchestrator.

```python
class AggregatorAction(str, Enum):
    DONE   = "done"
    REGEN  = "regen"
    REPLAN = "replan"
    HUMAN  = "human"

class AggregatorDecision(BaseModel):
    action: AggregatorAction
    summary: str                   # human-readable verdict summary for logs/UI
    failure_report: FailureReport | None = None   # populated only on replan-from-exhaustion
```

---

## JobState

Managed by the Task Manager. Persisted to disk after every state change.

```python
class JobStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    WAITING    = "waiting"         # blocked on human input
    DONE       = "done"
    FAILED     = "failed"

class JobState(BaseModel):
    job_id: str
    task_description: str
    status: JobStatus
    current_version: int           # increments on every plan or code snapshot
    verifier_retries: int = 0   # Plan Verifier → Planner revision cycles
    regen_retries: int = 0
    replan_retries: int = 0     # Aggregator → Planner replan cycles
    created_at: datetime
    updated_at: datetime
```
