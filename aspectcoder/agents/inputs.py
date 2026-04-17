from __future__ import annotations
from dataclasses import dataclass, field
from aspectcoder.models.plan import Plan
from aspectcoder.models.code import GeneratedCode
from aspectcoder.models.verdict import ReviewVerdict
from aspectcoder.models.aggregator import AttemptSummary


@dataclass
class PlannerInput:
    task_description: str
    codebase_context: str = ""
    previous_issues: list[str] = field(default_factory=list)


@dataclass
class GeneratorInput:
    plan: Plan
    codebase_context: str = ""
    retry_feedback: list[ReviewVerdict] = field(default_factory=list)


@dataclass
class ReviewInput:
    plan: Plan
    generated_code: list[GeneratedCode]


@dataclass
class AggregatorInput:
    verdicts: list[ReviewVerdict]
    regen_count: int
    task_id: str
    all_attempts: list[AttemptSummary] = field(default_factory=list)
