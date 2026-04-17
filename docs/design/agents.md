# Agents

Each agent extends `BaseAgent`, which handles LLM calls, prompt caching, structured output enforcement, and confidence emission. Agents implement a single `run(input) -> output` method.

---

## Planner

**Model:** `claude-opus-4-7`

**Responsibility:** Decompose the user's task into a structured, actionable plan.

**Input:**
- Task description (natural language)
- Codebase context (relevant file contents, git diff if available)
- On revision: previous `PlanVerdict` issues list

**Output:** `Plan`

**Behaviour:**
- Identifies subtasks, assigns each a target file and language
- Chooses an overall approach (e.g. "extend existing binary search, add bounds checking")
- Emits a confidence score; if < 0.4, sets `needs_human: true`
- Can be called up to 3 times per job (revision cycles driven by Plan Verifier feedback)

---

## Plan Verifier

**Model:** `claude-sonnet-4-6`

**Responsibility:** One-shot evaluation of the Planner's output. Does not iterate.

**Input:** `Plan`

**Output:** `PlanVerdict`

**Checks:**
- Feasibility — can the approach actually be implemented?
- Completeness — are all necessary subtasks present? Are dependencies covered?
- Language constraints — does the approach respect C/C++ memory model, JS async patterns, etc.?
- Scope — is the plan scoped to what the user asked, or does it over-reach?

**Behaviour:**
- Single LLM call per plan version
- Sets `pass: false` with a populated `issues` list on failure — Planner revises and resubmits
- Sets `needs_human: true` if the task description itself is ambiguous

---

## Generator

**Model:** `claude-sonnet-4-6` (Python, JavaScript) / `claude-opus-4-7` (C, C++)

**Responsibility:** Implement each subtask in the target language according to the approved Plan.

**Input:**
- Approved `Plan`
- Codebase context (target files)
- On retry: `ReviewVerdict` issues from previous attempt

**Output:** `GeneratedCode` per subtask

**Behaviour:**
- Implements subtasks in dependency order
- Language is detected per subtask from the Plan; model is selected accordingly
- On retry, reviewer feedback is injected into the prompt as explicit fix instructions
- Emits confidence per subtask; low confidence on a subtask triggers replan consideration

---

## Functional Reviewer

**Model:** `gpt-5-mini`

**Responsibility:** Verify that the generated code correctly implements the specification.

**Input:** `Plan` + `GeneratedCode`

**Output:** `ReviewVerdict` (reviewer: "functional")

**Checks:**
- Does the implementation match the subtask description?
- Are edge cases handled (empty input, null, overflow)?
- Is test coverage adequate (if tests are part of the plan)?
- Are function signatures and return types correct?

**Behaviour:**
- Always runs first in the review phase
- On failure, Security and Performance reviewers are skipped (early exit)
- Sets `approach_wrong: true` if the fundamental algorithm is incorrect for the problem

---

## Security Reviewer

**Model:** `claude-sonnet-4-6`

**Responsibility:** Identify security vulnerabilities in the generated code.

**Input:** `Plan` + `GeneratedCode`

**Output:** `ReviewVerdict` (reviewer: "security")

**Reference standards:** CWE Top 25 Most Dangerous Software Weaknesses and OWASP Secure Coding Practices — every finding should map to one or both.

**Checks:**
- **C/C++:** buffer overflows (CWE-787, CWE-125), use-after-free (CWE-416), integer overflow (CWE-190), format string bugs (CWE-134), race conditions (CWE-362)
- **Python:** injection risks (CWE-78, CWE-89), unsafe deserialization (CWE-502), insecure defaults
- **JavaScript:** XSS (CWE-79), prototype pollution, unsafe `eval` (CWE-95), insecure dependencies
- **All languages:** improper input validation (CWE-20), hard-coded credentials (CWE-798), missing authentication (CWE-306), other OWASP Top 10 violations

**Behaviour:**
- Runs in parallel with Performance Reviewer (only if Functional passes)
- Uses a stronger model than other reviewers given the high-stakes nature of security issues
- Sets `approach_wrong: true` only if the security flaw is architectural (e.g., a crypto design error), not just a patch

---

## Performance Reviewer

**Model:** `gpt-5-mini`

**Responsibility:** Evaluate algorithmic efficiency and resource usage.

**Input:** `Plan` + `GeneratedCode`

**Output:** `ReviewVerdict` (reviewer: "performance")

**Checks:**
- Time complexity — is the algorithm appropriate for the expected data scale?
- Memory usage — unnecessary allocations, leaks, large stack frames in C/C++
- Hot path analysis — are expensive operations in tight loops?
- Language-specific patterns — Python list comprehensions vs loops, JS async overhead

**Behaviour:**
- Runs in parallel with Security Reviewer (only if Functional passes)
- Sets `approach_wrong: true` only if the algorithm is fundamentally unsuitable (e.g., O(n²) where O(n log n) is required by the plan constraints)

---

## Aggregator

**Model:** `claude-haiku-4-5` (normal path) / `claude-sonnet-4-6` (failure report path)

**Responsibility:** Collect all reviewer verdicts and determine the next action.

**Input:** List of `ReviewVerdict`

**Output:** `AggregatorDecision`

**Routing logic (implemented in code, not by LLM):**

```python
if all(v.pass_ for v in verdicts):
    action = "done"
elif any(v.approach_wrong for v in verdicts):
    action = "replan"
elif regen_count >= 3:
    action = "replan"          # triggers failure report compilation
elif any(v.needs_human or v.confidence < 0.5 for v in verdicts):
    action = "human"
else:
    action = "regen"
```

**LLM call — normal path (Haiku):**
- Summarise reviewer verdicts into a human-readable job log entry
- Format structured feedback for the Generator's next prompt

**LLM call — failure report path (Sonnet):**
- Synthesise all reviewer outputs across all 3 regeneration attempts
- Identify recurring patterns (e.g., "security fails consistently on memory management in subtask 2")
- Write a diagnosis and replan hints for the Planner

See `data-models.md` for the `FailureReport` schema.
