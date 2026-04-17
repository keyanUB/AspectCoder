import json
import pytest
from unittest.mock import patch, MagicMock
from aspectcoder.config import ModelConfig, Config, ModelsConfig
from aspectcoder.llm.client import LLMResponse
from aspectcoder.agents.aggregator import AggregatorAgent
from aspectcoder.agents.inputs import AggregatorInput
from aspectcoder.models.verdict import ReviewVerdict, ReviewerType, Issue, IssueSeverity
from aspectcoder.models.aggregator import AggregatorDecision, AggregatorAction, AttemptSummary


def _make_config() -> Config:
    base = ModelConfig(model="claude-haiku-4-5", temperature=0.0, max_tokens=2048)
    sonnet = ModelConfig(model="claude-sonnet-4-6", temperature=0.3, max_tokens=4096)
    return Config(
        models=ModelsConfig(
            planner=ModelConfig(model="claude-opus-4-7"),
            generator={"default": base},
            verifier=base,
            reviewers={"functional": base, "security": base, "performance": base},
            aggregator={"normal": base, "failure_report": sonnet},
        )
    )


def _pass_verdict(reviewer: ReviewerType) -> ReviewVerdict:
    return ReviewVerdict(reviewer=reviewer, pass_=True, confidence=0.9)


def _fail_verdict(
    reviewer: ReviewerType,
    approach_wrong: bool = False,
    needs_human: bool = False,
    confidence: float = 0.7,
) -> ReviewVerdict:
    return ReviewVerdict(
        reviewer=reviewer,
        pass_=False,
        confidence=confidence,
        issues=[Issue(severity=IssueSeverity.MAJOR, description="Problem", location="", suggestion="Fix it")],
        approach_wrong=approach_wrong,
        needs_human=needs_human,
    )


@pytest.fixture
def agent():
    return AggregatorAgent(config=_make_config())


def _mock_summary_response(model: str = "claude-haiku-4-5") -> LLMResponse:
    return LLMResponse(
        content=json.dumps({"summary": "All reviewers passed."}),
        model=model,
        usage={"prompt_tokens": 20, "completion_tokens": 10},
    )


# ── Routing logic (no LLM required for these) ────────────────────────────────

def test_aggregator_routes_done_when_all_pass(agent):
    verdicts = [
        _pass_verdict(ReviewerType.FUNCTIONAL),
        _pass_verdict(ReviewerType.SECURITY),
        _pass_verdict(ReviewerType.PERFORMANCE),
    ]
    with patch.object(agent._normal_client, "call", return_value=_mock_summary_response()):
        decision = agent.run(AggregatorInput(verdicts=verdicts, regen_count=0, task_id="task-1"))
    assert decision.action == AggregatorAction.DONE


def test_aggregator_routes_replan_on_approach_wrong(agent):
    verdicts = [
        _fail_verdict(ReviewerType.FUNCTIONAL, approach_wrong=True),
    ]
    with patch.object(agent._normal_client, "call", return_value=_mock_summary_response()):
        decision = agent.run(AggregatorInput(verdicts=verdicts, regen_count=0, task_id="task-1"))
    assert decision.action == AggregatorAction.REPLAN


def test_aggregator_routes_regen_on_fixable_failure(agent):
    verdicts = [_fail_verdict(ReviewerType.FUNCTIONAL)]
    with patch.object(agent._normal_client, "call", return_value=_mock_summary_response()):
        decision = agent.run(AggregatorInput(verdicts=verdicts, regen_count=0, task_id="task-1"))
    assert decision.action == AggregatorAction.REGEN


def test_aggregator_routes_replan_when_regen_exhausted(agent):
    verdicts = [_fail_verdict(ReviewerType.FUNCTIONAL)]
    attempts = [AttemptSummary(attempt_number=i + 1, verdicts=verdicts) for i in range(3)]
    with patch.object(agent._failure_client, "call", return_value=LLMResponse(
        content=json.dumps({
            "summary": "Three attempts all failed.",
            "failure_report": {
                "task_id": "task-1",
                "attempts": [a.model_dump() for a in attempts],
                "recurring_patterns": ["Missing bounds check"],
                "diagnosis": "Algorithm does not handle edge cases",
                "replan_hints": ["Add bounds checking subtask"],
            },
        }),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 50, "completion_tokens": 80},
    )):
        decision = agent.run(AggregatorInput(
            verdicts=verdicts, regen_count=3, task_id="task-1", all_attempts=attempts
        ))
    assert decision.action == AggregatorAction.REPLAN
    assert decision.failure_report is not None
    assert len(decision.failure_report.replan_hints) == 1


def test_aggregator_routes_human_on_low_confidence_verdict(agent):
    verdicts = [_fail_verdict(ReviewerType.SECURITY, confidence=0.4)]
    with patch.object(agent._normal_client, "call", return_value=_mock_summary_response()):
        decision = agent.run(AggregatorInput(verdicts=verdicts, regen_count=0, task_id="task-1"))
    assert decision.action == AggregatorAction.HUMAN


def test_aggregator_routes_human_on_needs_human_verdict(agent):
    verdicts = [_fail_verdict(ReviewerType.FUNCTIONAL, needs_human=True)]
    with patch.object(agent._normal_client, "call", return_value=_mock_summary_response()):
        decision = agent.run(AggregatorInput(verdicts=verdicts, regen_count=0, task_id="task-1"))
    assert decision.action == AggregatorAction.HUMAN


def test_aggregator_uses_failure_client_when_regen_exhausted(agent):
    verdicts = [_fail_verdict(ReviewerType.FUNCTIONAL)]
    attempts = [AttemptSummary(attempt_number=1, verdicts=verdicts)]
    failure_response = LLMResponse(
        content=json.dumps({
            "summary": "Failed.",
            "failure_report": {
                "task_id": "task-1",
                "attempts": [a.model_dump() for a in attempts],
                "recurring_patterns": [],
                "diagnosis": "Algorithm wrong",
                "replan_hints": [],
            },
        }),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 50, "completion_tokens": 80},
    )
    with patch.object(agent._failure_client, "call", return_value=failure_response) as mock_fail, \
         patch.object(agent._normal_client, "call", return_value=_mock_summary_response()) as mock_normal:
        agent.run(AggregatorInput(verdicts=verdicts, regen_count=3, task_id="task-1", all_attempts=attempts))
    assert mock_fail.call_count == 1
    assert mock_normal.call_count == 0
