import json
import pytest
from unittest.mock import patch
from aspectcoder.config import ModelConfig
from aspectcoder.llm.client import LLMResponse
from aspectcoder.agents.reviewers.functional import FunctionalReviewerAgent
from aspectcoder.agents.reviewers.security import SecurityReviewerAgent, SecurityLevel
from aspectcoder.agents.reviewers.performance import PerformanceReviewerAgent
from aspectcoder.agents.inputs import ReviewInput
from aspectcoder.models.plan import Plan, Subtask
from aspectcoder.models.code import GeneratedCode
from aspectcoder.models.verdict import ReviewVerdict, ReviewerType


@pytest.fixture
def functional_config():
    return ModelConfig(model="gpt-5-mini", temperature=0.0, max_tokens=2048)


@pytest.fixture
def security_config():
    return ModelConfig(model="claude-sonnet-4-6", temperature=0.0, max_tokens=2048)


@pytest.fixture
def performance_config():
    return ModelConfig(model="gpt-5-mini", temperature=0.0, max_tokens=2048)


@pytest.fixture
def review_input():
    plan = Plan(
        task_id="task-1",
        task_description="Add binary_search to utils.c",
        approach="Iterative binary search",
        subtasks=[
            Subtask(id="subtask-1", description="Implement binary_search", target_file="src/utils.c", language="c")
        ],
        target_files=["src/utils.c"],
        primary_language="c",
        confidence=0.9,
    )
    code = [
        GeneratedCode(
            subtask_id="subtask-1",
            language="c",
            file_path="src/utils.c",
            code="int binary_search(int *arr, int n, int target) { return -1; }",
            explanation="Stub",
            confidence=0.85,
        )
    ]
    return ReviewInput(plan=plan, generated_code=code)


def _make_verdict(reviewer: str, pass_: bool = True, approach_wrong: bool = False, needs_human: bool = False) -> dict:
    return {
        "reviewer": reviewer,
        "pass_": pass_,
        "confidence": 0.9 if pass_ else 0.6,
        "issues": [] if pass_ else [
            {
                "severity": "major",
                "description": "Missing bounds check",
                "location": "src/utils.c:5",
                "suggestion": "Add n <= 0 guard",
            }
        ],
        "approach_wrong": approach_wrong,
        "needs_human": needs_human,
    }


# ── Functional Reviewer ──────────────────────────────────────────────────────

def test_functional_reviewer_returns_pass_verdict(functional_config, review_input):
    agent = FunctionalReviewerAgent(config=functional_config)
    mock_response = LLMResponse(
        content=json.dumps(_make_verdict("functional")),
        model="gpt-5-mini",
        usage={"prompt_tokens": 30, "completion_tokens": 20},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        result = agent.run(review_input)
    assert isinstance(result, ReviewVerdict)
    assert result.reviewer == ReviewerType.FUNCTIONAL
    assert result.pass_ is True


def test_functional_reviewer_returns_fail_with_approach_wrong(functional_config, review_input):
    agent = FunctionalReviewerAgent(config=functional_config)
    mock_response = LLMResponse(
        content=json.dumps(_make_verdict("functional", pass_=False, approach_wrong=True)),
        model="gpt-5-mini",
        usage={"prompt_tokens": 30, "completion_tokens": 30},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        result = agent.run(review_input)
    assert result.pass_ is False
    assert result.approach_wrong is True


def test_functional_reviewer_prompt_includes_plan_and_code(functional_config, review_input):
    agent = FunctionalReviewerAgent(config=functional_config)
    mock_response = LLMResponse(
        content=json.dumps(_make_verdict("functional")),
        model="gpt-5-mini",
        usage={"prompt_tokens": 30, "completion_tokens": 20},
    )
    captured = []
    with patch.object(agent.client, "call", side_effect=lambda msgs, **kw: captured.append(msgs) or mock_response):
        agent.run(review_input)
    combined = " ".join(m.content for m in captured[0])
    assert "binary_search" in combined
    assert "subtask-1" in combined


# ── Security Reviewer ─────────────────────────────────────────────────────────

def test_security_reviewer_returns_verdict_tagged_security(security_config, review_input):
    agent = SecurityReviewerAgent(config=security_config)
    mock_response = LLMResponse(
        content=json.dumps(_make_verdict("security")),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 30, "completion_tokens": 20},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        result = agent.run(review_input)
    assert result.reviewer == ReviewerType.SECURITY


def test_security_reviewer_prompt_references_cwe_top25_and_owasp(security_config, review_input):
    agent = SecurityReviewerAgent(config=security_config, level=SecurityLevel.STRICT)
    mock_response = LLMResponse(
        content=json.dumps(_make_verdict("security")),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 30, "completion_tokens": 20},
    )
    captured = []
    with patch.object(agent.client, "call", side_effect=lambda msgs, **kw: captured.append(msgs) or mock_response):
        agent.run(review_input)
    combined = " ".join(m.content for m in captured[0])
    assert "CWE Top 25" in combined
    assert "OWASP" in combined


def test_security_reviewer_basic_level_omits_cwe_and_owasp(security_config, review_input):
    agent = SecurityReviewerAgent(config=security_config, level=SecurityLevel.BASIC)
    mock_response = LLMResponse(
        content=json.dumps(_make_verdict("security")),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 10, "completion_tokens": 10},
    )
    captured = []
    with patch.object(agent.client, "call", side_effect=lambda msgs, **kw: captured.append(msgs) or mock_response):
        agent.run(review_input)
    combined = " ".join(m.content for m in captured[0])
    assert "CWE Top 25" not in combined
    assert "OWASP Secure Coding" not in combined


def test_security_reviewer_standard_level_includes_cwe_but_not_owasp_scp(security_config, review_input):
    agent = SecurityReviewerAgent(config=security_config, level=SecurityLevel.STANDARD)
    mock_response = LLMResponse(
        content=json.dumps(_make_verdict("security")),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 20, "completion_tokens": 15},
    )
    captured = []
    with patch.object(agent.client, "call", side_effect=lambda msgs, **kw: captured.append(msgs) or mock_response):
        agent.run(review_input)
    combined = " ".join(m.content for m in captured[0])
    assert "CWE Top 25" in combined
    assert "OWASP Secure Coding Practices" not in combined


def test_security_reviewer_default_level_is_standard(security_config, review_input):
    agent = SecurityReviewerAgent(config=security_config)
    assert agent.level == SecurityLevel.STANDARD


# ── Local knowledge embedded in prompt ───────────────────────────────────────

def _capture_call(agent, review_input):
    """Returns (messages, cached_prefix) from the first client.call invocation."""
    mock_response = LLMResponse(
        content=json.dumps(_make_verdict("security")),
        model="claude-sonnet-4-6",
        usage={"prompt_tokens": 50, "completion_tokens": 20},
    )
    captured = {}

    def fake_call(msgs, *, cached_prefix=None, **kw):
        captured["messages"] = msgs
        captured["cached_prefix"] = cached_prefix
        return mock_response

    with patch.object(agent.client, "call", side_effect=fake_call):
        agent.run(review_input)
    return captured


def test_security_standard_embeds_cwe25_in_cached_prefix(security_config, review_input):
    agent = SecurityReviewerAgent(config=security_config, level=SecurityLevel.STANDARD)
    captured = _capture_call(agent, review_input)
    prefix = captured["cached_prefix"]
    assert prefix is not None
    combined = " ".join(m.content for m in prefix)
    assert "CWE-79" in combined
    assert "CWE-787" in combined


def test_security_standard_does_not_embed_owasp_scp(security_config, review_input):
    agent = SecurityReviewerAgent(config=security_config, level=SecurityLevel.STANDARD)
    captured = _capture_call(agent, review_input)
    prefix = captured["cached_prefix"]
    combined = " ".join(m.content for m in prefix) if prefix else ""
    assert "Input Validation" not in combined or "OWASP Secure Coding" not in combined


def test_security_strict_embeds_both_cwe25_and_owasp_scp(security_config, review_input):
    agent = SecurityReviewerAgent(config=security_config, level=SecurityLevel.STRICT)
    captured = _capture_call(agent, review_input)
    prefix = captured["cached_prefix"]
    assert prefix is not None
    combined = " ".join(m.content for m in prefix)
    assert "CWE-79" in combined
    assert "OWASP Secure Coding Practices" in combined


def test_security_basic_has_no_cached_prefix(security_config, review_input):
    agent = SecurityReviewerAgent(config=security_config, level=SecurityLevel.BASIC)
    captured = _capture_call(agent, review_input)
    assert not captured["cached_prefix"]


def test_security_knowledge_messages_have_cache_flag_set(security_config, review_input):
    agent = SecurityReviewerAgent(config=security_config, level=SecurityLevel.STRICT)
    captured = _capture_call(agent, review_input)
    prefix = captured["cached_prefix"]
    assert all(m.cache for m in prefix)


# ── Performance Reviewer ──────────────────────────────────────────────────────

def test_performance_reviewer_returns_verdict_tagged_performance(performance_config, review_input):
    agent = PerformanceReviewerAgent(config=performance_config)
    mock_response = LLMResponse(
        content=json.dumps(_make_verdict("performance")),
        model="gpt-5-mini",
        usage={"prompt_tokens": 30, "completion_tokens": 20},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        result = agent.run(review_input)
    assert result.reviewer == ReviewerType.PERFORMANCE


def test_performance_reviewer_sets_needs_human(performance_config, review_input):
    agent = PerformanceReviewerAgent(config=performance_config)
    mock_response = LLMResponse(
        content=json.dumps(_make_verdict("performance", pass_=False, needs_human=True)),
        model="gpt-5-mini",
        usage={"prompt_tokens": 30, "completion_tokens": 25},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        agent.run(review_input)
    assert agent.last_needs_human is True
