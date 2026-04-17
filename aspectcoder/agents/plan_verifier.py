from __future__ import annotations
import json
from aspectcoder.llm.base_agent import BaseAgent
from aspectcoder.llm.client import LLMMessage
from aspectcoder.models.plan import Plan
from aspectcoder.models.verdict import PlanVerdict

_SYSTEM = """\
You are a code plan reviewer. Evaluate the given plan for:
- Feasibility: can the approach actually be implemented?
- Completeness: are all necessary subtasks present with dependencies covered?
- Language constraints: does the approach respect language-specific constraints (C memory model, JS async patterns, etc.)?
- Scope: is the plan scoped to what was asked, without over-reaching?

Respond with a single JSON object:
{
  "pass_": <true|false>,
  "confidence": <0.0–1.0>,
  "issues": ["<plain English description of each problem>", ...],
  "needs_human": <true|false>
}

Set pass_: false and populate issues if you find any problems.
Set needs_human: true only if the original task description is too ambiguous to evaluate.
"""


class PlanVerifierAgent(BaseAgent[Plan, PlanVerdict]):
    def build_messages(self, input: Plan) -> list[dict]:
        plan_json = input.model_dump_json(indent=2)
        return [
            LLMMessage(role="system", content=_SYSTEM),
            LLMMessage(role="user", content=f"Evaluate this plan:\n\n{plan_json}"),
        ]

    def parse_output(self, raw: str) -> PlanVerdict:
        data = json.loads(raw)
        return PlanVerdict(**data)
