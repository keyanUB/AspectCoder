import json
import pytest
from unittest.mock import patch
from aspectcoder.config import ModelConfig
from aspectcoder.llm.client import LLMResponse
from aspectcoder.agents.generator import GeneratorAgent
from aspectcoder.agents.inputs import GeneratorInput
from aspectcoder.models.plan import Plan, Subtask
from aspectcoder.models.code import GenerationResult, GeneratedCode
from aspectcoder.models.verdict import ReviewVerdict, ReviewerType, Issue, IssueSeverity


@pytest.fixture
def config():
    return ModelConfig(model="claude-sonnet-4-6", temperature=0.2, max_tokens=4096)


@pytest.fixture
def agent(config):
    return GeneratorAgent(config=config)


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


def _make_result(needs_human: bool = False, confidence: float = 0.85) -> dict:
    return {
        "subtasks": [
            {
                "subtask_id": "subtask-1",
                "language": "c",
                "file_path": "src/utils.c",
                "code": "int binary_search(int *arr, int n, int target) { return -1; }",
                "explanation": "Iterative binary search",
                "confidence": confidence,
                "needs_human": needs_human,
            }
        ],
        "needs_human": needs_human,
    }


def test_generator_returns_generation_result(agent, sample_plan):
    mock_response = LLMResponse(
        content=json.dumps(_make_result()),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 30, "completion_tokens": 60},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        result = agent.run(GeneratorInput(plan=sample_plan))
    assert isinstance(result, GenerationResult)
    assert len(result.subtasks) == 1
    assert result.subtasks[0].subtask_id == "subtask-1"
    assert agent.last_needs_human is False


def test_generator_sets_needs_human_when_output_requests_it(agent, sample_plan):
    mock_response = LLMResponse(
        content=json.dumps(_make_result(needs_human=True, confidence=0.3)),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 30, "completion_tokens": 60},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        agent.run(GeneratorInput(plan=sample_plan))
    assert agent.last_needs_human is True


def test_generator_prompt_includes_plan(agent, sample_plan):
    mock_response = LLMResponse(
        content=json.dumps(_make_result()),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 30, "completion_tokens": 60},
    )
    captured = []
    with patch.object(agent.client, "call", side_effect=lambda msgs, **kw: captured.append(msgs) or mock_response):
        agent.run(GeneratorInput(plan=sample_plan))
    combined = " ".join(m.content for m in captured[0])
    assert "binary_search" in combined
    assert "subtask-1" in combined


def test_generator_prompt_includes_retry_feedback(agent, sample_plan):
    feedback = [
        ReviewVerdict(
            reviewer=ReviewerType.FUNCTIONAL,
            pass_=False,
            confidence=0.7,
            issues=[
                Issue(
                    severity=IssueSeverity.MAJOR,
                    description="Missing bounds check",
                    location="src/utils.c:10",
                    suggestion="Add check for n <= 0",
                )
            ],
        )
    ]
    mock_response = LLMResponse(
        content=json.dumps(_make_result()),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 30, "completion_tokens": 60},
    )
    captured = []
    with patch.object(agent.client, "call", side_effect=lambda msgs, **kw: captured.append(msgs) or mock_response):
        agent.run(GeneratorInput(plan=sample_plan, retry_feedback=feedback))
    combined = " ".join(m.content for m in captured[0])
    assert "bounds check" in combined


def test_generator_prompt_includes_codebase_context(agent, sample_plan):
    mock_response = LLMResponse(
        content=json.dumps(_make_result()),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 30, "completion_tokens": 60},
    )
    captured = []
    with patch.object(agent.client, "call", side_effect=lambda msgs, **kw: captured.append(msgs) or mock_response):
        agent.run(GeneratorInput(
            plan=sample_plan,
            codebase_context="// src/utils.c\nint existing_fn() { return 42; }",
        ))
    combined = " ".join(m.content for m in captured[0])
    assert "existing_fn" in combined
