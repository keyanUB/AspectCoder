from __future__ import annotations
import json
from aspectcoder.llm.base_agent import BaseAgent
from aspectcoder.llm.client import LLMMessage
from aspectcoder.agents.inputs import GeneratorInput
from aspectcoder.models.code import GenerationResult
from aspectcoder.models.verdict import ReviewVerdict

_SYSTEM = """\
You are a code generator. Implement each subtask in the approved plan exactly as specified.

Respond with a single JSON object:
{
  "subtasks": [
    {
      "subtask_id": "<subtask id from plan>",
      "language": "<python|c|cpp|javascript>",
      "file_path": "<target file path>",
      "code": "<complete implementation>",
      "explanation": "<brief rationale for key choices>",
      "confidence": <0.0–1.0>,
      "needs_human": <true|false>
    }
  ],
  "needs_human": <true|false>
}

Implement subtasks in dependency order (subtasks with no dependencies first).
Set needs_human: true on a subtask if the specification is too ambiguous to implement safely.
Set confidence < 0.4 if you believe the plan itself is unimplementable.
"""


def _format_feedback(verdicts: list[ReviewVerdict]) -> str:
    lines = ["Fix the following issues from the previous attempt:"]
    for v in verdicts:
        lines.append(f"\n[{v.reviewer.value.upper()} REVIEWER]")
        for issue in v.issues:
            lines.append(
                f"  [{issue.severity.value.upper()}] {issue.description}"
                + (f" at {issue.location}" if issue.location else "")
                + f"\n  Fix: {issue.suggestion}"
            )
    return "\n".join(lines)


class GeneratorAgent(BaseAgent[GeneratorInput, GenerationResult]):
    def build_messages(self, input: GeneratorInput) -> list[dict]:
        parts = [f"Plan:\n{input.plan.model_dump_json(indent=2)}"]

        if input.codebase_context:
            parts.append(f"Codebase context:\n{input.codebase_context}")

        if input.retry_feedback:
            parts.append(_format_feedback(input.retry_feedback))

        return [
            LLMMessage(role="system", content=_SYSTEM),
            LLMMessage(role="user", content="\n\n".join(parts)),
        ]

    def parse_output(self, raw: str) -> GenerationResult:
        data = json.loads(raw)
        return GenerationResult(**data)
