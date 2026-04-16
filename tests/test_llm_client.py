import pytest
from unittest.mock import patch, MagicMock
from mycoder.llm.client import LLMClient, LLMMessage, LLMResponse
from mycoder.config import ModelConfig

@pytest.fixture
def model_config():
    return ModelConfig(model="claude-haiku-4-5", temperature=0.0, max_tokens=512)

@pytest.fixture
def client(model_config):
    return LLMClient(config=model_config)

def test_llm_message_roles():
    msg = LLMMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"

def test_llm_response_fields():
    resp = LLMResponse(content="Hello back", model="claude-haiku-4-5", usage={"prompt_tokens": 5, "completion_tokens": 3})
    assert resp.content == "Hello back"

def test_call_invokes_litellm(client):
    messages = [LLMMessage(role="user", content="Say hi")]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Hi!"
    mock_response.model = "claude-haiku-4-5"
    mock_response.usage.prompt_tokens = 5
    mock_response.usage.completion_tokens = 2

    with patch("mycoder.llm.client.litellm.completion", return_value=mock_response) as mock_call:
        response = client.call(messages)
        mock_call.assert_called_once()
        assert response.content == "Hi!"

def test_call_applies_cache_prefix(client):
    cached = [LLMMessage(role="user", content="Cached context", cache=True)]
    dynamic = [LLMMessage(role="user", content="New question")]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Answer"
    mock_response.model = "claude-haiku-4-5"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    with patch("mycoder.llm.client.litellm.completion", return_value=mock_response) as mock_call:
        client.call(dynamic, cached_prefix=cached)
        call_kwargs = mock_call.call_args
        messages_sent = call_kwargs[1]["messages"]
        assert len(messages_sent) == 2
