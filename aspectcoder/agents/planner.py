from __future__ import annotations
import json
from aspectcoder.llm.base_agent import BaseAgent
from aspectcoder.llm.client import LLMMessage
from aspectcoder.agents.inputs import PlannerInput
from aspectcoder.models.plan import Plan

_SYSTEM = """\
You are a software architect. Your job is to decompose a coding task into a structured, actionable plan.

Respond with a single JSON object matching this schema exactly:
{
  "task_id": "<unique id, e.g. task-1>",
  "task_description": "<the original task>",
  "approach": "<high-level strategy in plain English>",
  "subtasks": [
    {
      "id": "<subtask-N>",
      "description": "<what to implement>",
      "target_file": "<path/to/file>",
      "language": "<python|c|cpp|javascript>",
      "dependencies": ["<subtask-id>", ...]
    }
  ],
  "target_files": ["<all files that will be modified or created>"],
  "primary_language": "<dominant language>",
  "confidence": <0.0–1.0>,
  "needs_human": <true|false>
}

Set needs_human: true only if the task description is genuinely ambiguous and you cannot proceed without clarification.
Set confidence < 0.4 if you are unsure the approach is implementable.
"""


class PlannerAgent(BaseAgent[PlannerInput, Plan]):
    def build_messages(self, input: PlannerInput) -> list[dict]:
        parts = [f"Task: {input.task_description}"]

        if input.codebase_context:
            parts.append(f"Codebase context:\n{input.codebase_context}")

        if input.previous_issues:
            issues_text = "\n".join(f"- {issue}" for issue in input.previous_issues)
            parts.append(
                f"Your previous plan was rejected. Please revise it to address these issues:\n{issues_text}"
            )

        return [
            LLMMessage(role="system", content=_SYSTEM),
            LLMMessage(role="user", content="\n\n".join(parts)),
        ]

    def parse_output(self, raw: str) -> Plan:
        data = json.loads(raw)
        return Plan(**data)
