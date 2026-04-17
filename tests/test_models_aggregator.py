import pytest
from aspectcoder.models.verdict import ReviewVerdict, ReviewerType
from aspectcoder.models.aggregator import (
    AttemptSummary, FailureReport, AggregatorAction, AggregatorDecision
)

def test_aggregator_action_values():
    assert AggregatorAction.DONE   == "done"
    assert AggregatorAction.REGEN  == "regen"
    assert AggregatorAction.REPLAN == "replan"
    assert AggregatorAction.HUMAN  == "human"

def test_aggregator_decision_done():
    decision = AggregatorDecision(action=AggregatorAction.DONE, summary="All reviewers passed.")
    assert decision.failure_report is None

def test_failure_report_valid():
    verdict = ReviewVerdict(
        reviewer=ReviewerType.SECURITY,
        pass_=False,
        confidence=0.3,
        issues=[],
    )
    attempt = AttemptSummary(attempt_number=1, verdicts=[verdict])
    report = FailureReport(
        task_id="job-abc123",
        attempts=[attempt],
        recurring_patterns=["Security consistently fails on memory management in subtask-1"],
        diagnosis="Plan does not specify buffer ownership — Generator cannot infer safe bounds.",
        replan_hints=["Specify in subtask-1 that the caller owns the buffer and passes length explicitly."],
    )
    assert report.task_id == "job-abc123"
    assert len(report.attempts) == 1

def test_aggregator_decision_replan_has_report():
    report = FailureReport(
        task_id="job-abc123",
        attempts=[],
        recurring_patterns=[],
        diagnosis="Approach is wrong.",
        replan_hints=[],
    )
    decision = AggregatorDecision(
        action=AggregatorAction.REPLAN,
        summary="3 regenerations exhausted.",
        failure_report=report,
    )
    assert decision.failure_report is not None
