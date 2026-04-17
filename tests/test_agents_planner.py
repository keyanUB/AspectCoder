import json
import pytest
from unittest.mock import patch
from aspectcoder.config import ModelConfig
from aspectcoder.llm.client import LLMResponse
from aspectcoder.agents.planner import PlannerAgent
from aspectcoder.agents.inputs import PlannerInput
from aspectcoder.models.plan import Plan


@pytest.fixture
def config():
    return ModelConfig(model="claude-opus-4-7", temperature=0.7, max_tokens=4096)


@pytest.fixture
def agent(config):
    return PlannerAgent(config=config)


def _make_plan(task_id: str = "task-1", needs_human: bool = False, confidence: float = 0.9) -> dict:
    return {
        "task_id": task_id,
        "task_description": "Add binary_search to utils.c",
        "approach": "Implement iterative binary search with bounds checking",
        "subtasks": [
            {
                "id": "subtask-1",
                "description": "Implement binary_search function",
                "target_file": "src/utils.c",
                "language": "c",
                "dependencies": [],
            }
        ],
        "target_files": ["src/utils.c"],
        "primary_language": "c",
        "confidence": confidence,
        "needs_human": needs_human,
    }


def test_planner_returns_plan(agent):
    mock_response = LLMResponse(
        content=json.dumps(_make_plan()),
        model="claude-opus-4-7",
        usage={"prompt_tokens": 10, "completion_tokens": 50},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        result = agent.run(PlannerInput(task_description="Add binary_search to utils.c"))
    assert isinstance(result, Plan)
    assert result.task_id == "task-1"
    assert len(result.subtasks) == 1
    assert agent.last_needs_human is False


def test_planner_sets_needs_human_when_output_requests_it(agent):
    mock_response = LLMResponse(
        content=json.dumps(_make_plan(needs_human=True, confidence=0.3)),
        model="claude-opus-4-7",
        usage={"prompt_tokens": 10, "completion_tokens": 50},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        agent.run(PlannerInput(task_description="ambiguous task"))
    assert agent.last_needs_human is True


def _extract_text(msgs) -> str:
    return " ".join(m.content for m in msgs)


def test_planner_prompt_includes_task_description(agent):
    mock_response = LLMResponse(
        content=json.dumps(_make_plan()),
        model="claude-opus-4-7",
        usage={"prompt_tokens": 10, "completion_tokens": 50},
    )
    captured = []
    with patch.object(agent.client, "call", side_effect=lambda msgs, **kw: captured.append(msgs) or mock_response):
        agent.run(PlannerInput(task_description="Add binary_search to utils.c"))
    assert "binary_search" in _extract_text(captured[0])


def test_planner_prompt_includes_previous_issues_on_revision(agent):
    mock_response = LLMResponse(
        content=json.dumps(_make_plan()),
        model="claude-opus-4-7",
        usage={"prompt_tokens": 10, "completion_tokens": 50},
    )
    captured = []
    with patch.object(agent.client, "call", side_effect=lambda msgs, **kw: captured.append(msgs) or mock_response):
        agent.run(PlannerInput(
            task_description="Add binary_search",
            previous_issues=["Subtask 1 is missing bounds checking", "No error handling"],
        ))
    assert "bounds checking" in _extract_text(captured[0])


def test_planner_prompt_includes_codebase_context(agent):
    mock_response = LLMResponse(
        content=json.dumps(_make_plan()),
        model="claude-opus-4-7",
        usage={"prompt_tokens": 10, "completion_tokens": 50},
    )
    captured = []
    with patch.object(agent.client, "call", side_effect=lambda msgs, **kw: captured.append(msgs) or mock_response):
        agent.run(PlannerInput(
            task_description="Add binary_search",
            codebase_context="// src/utils.c\nint existing_function() { return 0; }",
        ))
    assert "existing_function" in _extract_text(captured[0])
