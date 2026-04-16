# tests/test_base_agent.py
import pytest
from unittest.mock import patch, MagicMock
from pydantic import BaseModel
from mycoder.config import ModelConfig
from mycoder.llm.base_agent import BaseAgent
from mycoder.llm.client import LLMResponse


class EchoOutput(BaseModel):
    message: str
    confidence: float


class EchoAgent(BaseAgent[str, EchoOutput]):
    """Minimal agent for testing — echoes the input."""

    def build_messages(self, input: str):
        return [{"role": "user", "content": input}]

    def parse_output(self, raw: str) -> EchoOutput:
        import json
        data = json.loads(raw)
        return EchoOutput(**data)


@pytest.fixture
def model_config():
    return ModelConfig(model="claude-haiku-4-5", temperature=0.0, max_tokens=512)


@pytest.fixture
def agent(model_config):
    return EchoAgent(config=model_config)


def test_agent_run_returns_output(agent):
    mock_response = LLMResponse(
        content='{"message": "hello", "confidence": 0.9}',
        model="claude-haiku-4-5",
        usage={"prompt_tokens": 5, "completion_tokens": 10},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        output = agent.run("hello")
        assert output.message == "hello"
        assert output.confidence == 0.9


def test_agent_triggers_needs_human_on_low_confidence(agent):
    mock_response = LLMResponse(
        content='{"message": "unsure", "confidence": 0.3}',
        model="claude-haiku-4-5",
        usage={"prompt_tokens": 5, "completion_tokens": 10},
    )
    with patch.object(agent.client, "call", return_value=mock_response):
        output = agent.run("ambiguous input")
        assert output.confidence == 0.3
        assert agent.last_needs_human is True


def test_agent_run_retries_on_parse_failure(agent):
    bad_response = LLMResponse(
        content="not valid json",
        model="claude-haiku-4-5",
        usage={"prompt_tokens": 5, "completion_tokens": 3},
    )
    good_response = LLMResponse(
        content='{"message": "ok", "confidence": 0.8}',
        model="claude-haiku-4-5",
        usage={"prompt_tokens": 5, "completion_tokens": 10},
    )
    with patch.object(agent.client, "call", side_effect=[bad_response, good_response]):
        output = agent.run("retry test")
        assert output.message == "ok"
