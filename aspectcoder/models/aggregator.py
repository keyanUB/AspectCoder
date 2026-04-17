from __future__ import annotations
from enum import Enum
from pydantic import BaseModel
from aspectcoder.models.verdict import ReviewVerdict
from aspectcoder.models.code import GenerationResult


class AttemptSummary(BaseModel):
    attempt_number: int
    verdicts: list[ReviewVerdict]
    generated_code: GenerationResult | None = None


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
