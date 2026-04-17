from __future__ import annotations
import json
from aspectcoder.llm.base_agent import BaseAgent
from aspectcoder.llm.client import LLMMessage
from aspectcoder.agents.inputs import ReviewInput
from aspectcoder.models.verdict import ReviewVerdict

_VERDICT_SCHEMA = """\
{
  "reviewer": "<functional|security|performance>",
  "pass_": <true|false>,
  "confidence": <0.0–1.0>,
  "issues": [
    {
      "severity": "<critical|major|minor>",
      "description": "<what is wrong>",
      "location": "<file:line or empty string>",
      "suggestion": "<concrete fix>"
    }
  ],
  "approach_wrong": <true|false>,
  "needs_human": <true|false>
}

Set pass_: false and list issues when you find problems.
Set approach_wrong: true only when the fundamental algorithm or design is incorrect — not just a fixable bug.
Set needs_human: true only when you cannot evaluate without additional clarification.
"""


class BaseReviewerAgent(BaseAgent[ReviewInput, ReviewVerdict]):
    """Shared structure for all code reviewer agents."""

    @property
    def reviewer_name(self) -> str:
        raise NotImplementedError

    @property
    def reviewer_focus(self) -> str:
        raise NotImplementedError

    def build_messages(self, input: ReviewInput) -> list[dict]:
        plan_json = input.plan.model_dump_json(indent=2)
        code_json = json.dumps(
            [c.model_dump() for c in input.generated_code], indent=2
        )
        system = (
            f"You are a {self.reviewer_name} reviewer. "
            f"Focus exclusively on: {self.reviewer_focus}\n\n"
            f"Respond with this JSON schema:\n{_VERDICT_SCHEMA}"
        )
        user = (
            f"Plan:\n{plan_json}\n\n"
            f"Generated code:\n{code_json}"
        )
        return [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user),
        ]

    def parse_output(self, raw: str) -> ReviewVerdict:
        data = json.loads(raw)
        return ReviewVerdict(**data)
