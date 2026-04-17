from __future__ import annotations
import json
from aspectcoder.config import Config
from aspectcoder.llm.client import LLMClient, LLMMessage
from aspectcoder.llm.base_agent import _strip_fences
from aspectcoder.agents.inputs import AggregatorInput
from aspectcoder.models.verdict import ReviewVerdict
from aspectcoder.models.aggregator import (
    AggregatorAction,
    AggregatorDecision,
    FailureReport,
    AttemptSummary,
)

_NORMAL_SYSTEM = """\
You are a code review summariser. Given a list of reviewer verdicts, write a concise human-readable summary.

Respond with a single JSON object:
{"summary": "<one or two sentence summary of what passed and what failed>"}
"""

_FAILURE_SYSTEM = """\
You are a failure analyst. Three consecutive code generation attempts have all failed review.
Synthesise the reviewer outputs, identify recurring patterns, and write a diagnosis with replan hints.

Respond with this JSON:
{
  "summary": "<brief summary of why all attempts failed>",
  "failure_report": {
    "task_id": "<task id>",
    "attempts": <the attempts array you were given>,
    "recurring_patterns": ["<pattern observed across attempts>"],
    "diagnosis": "<root cause hypothesis in plain English>",
    "replan_hints": ["<specific suggestion for the Planner>"]
  }
}
"""


def _route(verdicts: list[ReviewVerdict], regen_count: int) -> AggregatorAction:
    if all(v.pass_ for v in verdicts):
        return AggregatorAction.DONE
    if any(v.approach_wrong for v in verdicts):
        return AggregatorAction.REPLAN
    if regen_count >= 3:
        return AggregatorAction.REPLAN
    if any(v.needs_human or v.confidence < 0.5 for v in verdicts):
        return AggregatorAction.HUMAN
    return AggregatorAction.REGEN


class AggregatorAgent:
    def __init__(self, config: Config):
        self._normal_client = LLMClient(config.models.aggregator["normal"])
        self._failure_client = LLMClient(config.models.aggregator["failure_report"])

    def run(self, input: AggregatorInput) -> AggregatorDecision:
        action = _route(input.verdicts, input.regen_count)

        if input.regen_count >= 3:
            return self._run_failure_path(input, action)
        return self._run_normal_path(input, action)

    def _run_normal_path(self, input: AggregatorInput, action: AggregatorAction) -> AggregatorDecision:
        verdicts_json = json.dumps([v.model_dump() for v in input.verdicts], indent=2)
        messages = [
            LLMMessage(role="system", content=_NORMAL_SYSTEM),
            LLMMessage(role="user", content=f"Verdicts:\n{verdicts_json}"),
        ]
        response = self._normal_client.call(messages)
        data = json.loads(_strip_fences(response.content))
        return AggregatorDecision(action=action, summary=data["summary"])

    def _run_failure_path(self, input: AggregatorInput, action: AggregatorAction) -> AggregatorDecision:
        attempts_json = json.dumps([a.model_dump() for a in input.all_attempts], indent=2)
        messages = [
            LLMMessage(role="system", content=_FAILURE_SYSTEM),
            LLMMessage(
                role="user",
                content=f"Task ID: {input.task_id}\n\nAll attempts:\n{attempts_json}",
            ),
        ]
        response = self._failure_client.call(messages)
        data = json.loads(_strip_fences(response.content))
        failure_report = FailureReport(**data["failure_report"]) if "failure_report" in data else None
        return AggregatorDecision(
            action=action,
            summary=data["summary"],
            failure_report=failure_report,
        )
