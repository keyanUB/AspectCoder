import json
import pytest
from unittest.mock import patch
from aspectcoder.config import ModelConfig
from aspectcoder.llm.client import LLMResponse
from aspectcoder.agents.plan_verifier import PlanVerifierAgent
from aspectcoder.models.plan import Plan, Subtask
from aspectcoder.models.verdict import PlanVerdict


@pytest.fixture
def config():
    return ModelConfig(model="claude-sonnet-4-6", temperature=0.0, max_tokens=2048)


@pytest.fixture
def agent(config):
    return PlanVerifierAgent(config=config)


@pytest.fixture
def sample_plan():
    return Plan(
        task_id="task-1",
        task_description="Add binary_search to utils.c",
        approach="Implement iterative binary search",
        subtasks=[
            Subtask(
                id="subtask-1",
                description="Implement binary_search",
                target_file="src/utils.c",
                language="c",
            )
        ],
        target_files=["src/utils.c"],
        primary_language="c",
        confidence=0.9,
    )


def test_verifier_returns_pass_verdict(agent, sample_plan):
    verdict_data = {"pass_": True, "confidence": 0.95, "issues": [], "needs_human": False}
    mock_response = LLMResponse(
        content=json.dumps(verdict_data),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 20, "completion_tokens": 15},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        result = agent.run(sample_plan)
    assert isinstance(result, PlanVerdict)
    assert result.pass_ is True
    assert result.confidence == 0.95
    assert agent.last_needs_human is False


def test_verifier_returns_fail_verdict_with_issues(agent, sample_plan):
    verdict_data = {
        "pass_": False,
        "confidence": 0.6,
        "issues": ["Missing bounds checking subtask", "No error handling for empty array"],
        "needs_human": False,
    }
    mock_response = LLMResponse(
        content=json.dumps(verdict_data),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 20, "completion_tokens": 30},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        result = agent.run(sample_plan)
    assert result.pass_ is False
    assert len(result.issues) == 2
    assert "bounds checking" in result.issues[0]


def test_verifier_sets_needs_human_on_ambiguous_task(agent, sample_plan):
    verdict_data = {
        "pass_": False,
        "confidence": 0.4,
        "issues": ["Task description is ambiguous"],
        "needs_human": True,
    }
    mock_response = LLMResponse(
        content=json.dumps(verdict_data),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 20, "completion_tokens": 20},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        agent.run(sample_plan)
    assert agent.last_needs_human is True


def test_verifier_prompt_includes_plan_json(agent, sample_plan):
    verdict_data = {"pass_": True, "confidence": 0.9, "issues": [], "needs_human": False}
    mock_response = LLMResponse(
        content=json.dumps(verdict_data),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 20, "completion_tokens": 15},
    )
    captured = []
    with patch.object(agent.client, "call", side_effect=lambda msgs, **kw: captured.append(msgs) or mock_response):
        agent.run(sample_plan)
    combined = " ".join(m.content for m in captured[0])
    assert "binary_search" in combined
    assert "subtask-1" in combined
