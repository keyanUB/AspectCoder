import pytest
from aspectcoder.models.verdict import (
    Issue, IssueSeverity, PlanVerdict, ReviewVerdict, ReviewerType
)

def test_issue_severity_values():
    assert IssueSeverity.CRITICAL == "critical"
    assert IssueSeverity.MAJOR == "major"
    assert IssueSeverity.MINOR == "minor"

def test_issue_valid():
    issue = Issue(
        severity=IssueSeverity.MAJOR,
        description="Buffer overflow in binary_search at line 42",
        location="src/utils.c:42",
        suggestion="Add bounds check: if (mid < 0 || mid >= len) return -1;",
    )
    assert issue.severity == IssueSeverity.MAJOR

def test_plan_verdict_pass():
    verdict = PlanVerdict(pass_=True, confidence=0.95, issues=[])
    assert verdict.pass_ is True
    assert verdict.needs_human is False

def test_plan_verdict_fail():
    verdict = PlanVerdict(
        pass_=False,
        confidence=0.4,
        issues=["Missing error handling subtask"],
        needs_human=False,
    )
    assert verdict.pass_ is False
    assert len(verdict.issues) == 1

def test_review_verdict_approach_wrong():
    verdict = ReviewVerdict(
        reviewer=ReviewerType.FUNCTIONAL,
        pass_=False,
        confidence=0.3,
        issues=[],
        approach_wrong=True,
    )
    assert verdict.approach_wrong is True

def test_review_verdict_serialises():
    verdict = ReviewVerdict(
        reviewer=ReviewerType.SECURITY,
        pass_=True,
        confidence=0.88,
        issues=[],
    )
    data = verdict.model_dump()
    restored = ReviewVerdict.model_validate(data)
    assert restored.reviewer == ReviewerType.SECURITY
