# LLM Configuration

## Model Assignments

| Agent | Model | Rationale |
|---|---|---|
| Planner | `claude-opus-4-7` | Complex decomposition and architectural reasoning |
| Plan Verifier | `claude-sonnet-4-6` | Structured one-shot evaluation |
| Generator (Python, JS) | `claude-sonnet-4-6` | Strong code generation, cost-efficient |
| Generator (C, C++) | `claude-opus-4-7` | Memory safety, undefined behaviour, complex pointer logic |
| Functional Reviewer | `gpt-5-mini` | Pattern-matching correctness check |
| Security Reviewer | `claude-sonnet-4-6` | High stakes — subtle C/C++ vulnerabilities need deeper reasoning |
| Performance Reviewer | `gpt-5-mini` | Complexity and memory analysis, well-suited to smaller models |
| Aggregator (normal) | `claude-haiku-4-5` | Merge structured verdicts — routing logic is in code |
| Aggregator (failure report) | `claude-sonnet-4-6` | Synthesise 9 reviewer outputs, write diagnosis for Planner |

The Aggregator model is selected at runtime:

```python
model = (
    "claude-sonnet-4-6" if regen_count >= 3
    else "claude-haiku-4-5"
)
```

---

## config.yaml

All model settings are driven by a single config file. No model name is hardcoded in agent logic.

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
    c:
      model: claude-opus-4-7
      temperature: 0.2
    cpp:
      model: claude-opus-4-7
      temperature: 0.2

  verifier:
    model: claude-sonnet-4-6
    temperature: 0.0            # deterministic for evaluation tasks

  reviewers:
    functional:
      model: gpt-5-mini
      temperature: 0.0
    security:
      model: claude-sonnet-4-6
      temperature: 0.0
    performance:
      model: gpt-5-mini
      temperature: 0.0

  aggregator:
    normal:
      model: claude-haiku-4-5
      temperature: 0.0
    failure_report:
      model: claude-sonnet-4-6
      temperature: 0.3          # slight creativity for diagnosis writing

api_keys:
  anthropic: ${ANTHROPIC_API_KEY}
  openai:    ${OPENAI_API_KEY}
```

---

## LiteLLM Abstraction Stack

```
Agent (PlannerAgent, GeneratorAgent, …)
   │  calls self.llm(messages, response_schema)
   ▼
BaseAgent
   │  injects system prompt
   │  applies cache_control headers to static prefix
   │  enforces response_schema via LiteLLM structured output
   │  handles timeouts and retries (network-level, not logic-level)
   ▼
LiteLLM completion()
   │  routes by model name prefix:
   │    claude-* → Anthropic SDK
   │    gpt-*    → OpenAI SDK
   │    ollama/* → Ollama local
   ▼
Provider API
```

Agents never import `anthropic` or `openai` directly. All provider-specific behaviour is handled by LiteLLM.

---

## Prompt Caching Strategy

Static context is cached once per job and reused across all agent calls, paying only for the dynamic (new) portion on retries.

| Cache key | Content | Reused by |
|---|---|---|
| `task` | Task description | All agents |
| `codebase` | Relevant file contents, git diff | Planner, Generator, all Reviewers |
| `plan` | Approved Plan JSON | Generator, all Reviewers |
| `previous_code` | Last GeneratedCode | Reviewers on retry |

On Anthropic models, `cache_control: {"type": "ephemeral"}` is applied to these prefix blocks. On OpenAI, LiteLLM handles equivalent caching where supported.

A retry call — where only the reviewer feedback is new — pays for:
- Dynamic tokens: the feedback message (small)
- Cached tokens: task + codebase + plan (large, but priced at cache rate)

This reduces retry costs by 40–60% on average.
