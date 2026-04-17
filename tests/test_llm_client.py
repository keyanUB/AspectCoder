import pytest
from unittest.mock import patch, MagicMock
from aspectcoder.llm.client import LLMClient, LLMMessage, LLMResponse
from aspectcoder.config import ModelConfig

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

    with patch("aspectcoder.llm.client.litellm.completion", return_value=mock_response) as mock_call:
        response = client.call(messages)
        mock_call.assert_called_once()
        assert response.content == "Hi!"

def test_claude_model_does_not_send_temperature(client):
    messages = [LLMMessage(role="user", content="Hi")]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Hi!"
    mock_response.model = "claude-haiku-4-5"
    mock_response.usage.prompt_tokens = 5
    mock_response.usage.completion_tokens = 2

    with patch("aspectcoder.llm.client.litellm.completion", return_value=mock_response) as mock_call:
        client.call(messages)
        kwargs = mock_call.call_args[1]
        assert "temperature" not in kwargs


def test_gpt5_model_does_not_send_temperature():
    config = ModelConfig(model="gpt-5-mini", temperature=0.0, max_tokens=512)
    gpt5_client = LLMClient(config=config)
    messages = [LLMMessage(role="user", content="Hi")]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Hi!"
    mock_response.model = "gpt-5-mini"
    mock_response.usage.prompt_tokens = 5
    mock_response.usage.completion_tokens = 2

    with patch("aspectcoder.llm.client.litellm.completion", return_value=mock_response) as mock_call:
        gpt5_client.call(messages)
        kwargs = mock_call.call_args[1]
        assert "temperature" not in kwargs


def test_gpt4_model_sends_temperature():
    config = ModelConfig(model="gpt-4o-mini", temperature=0.7, max_tokens=512)
    gpt4_client = LLMClient(config=config)
    messages = [LLMMessage(role="user", content="Hi")]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Hi!"
    mock_response.model = "gpt-4o-mini"
    mock_response.usage.prompt_tokens = 5
    mock_response.usage.completion_tokens = 2

    with patch("aspectcoder.llm.client.litellm.completion", return_value=mock_response) as mock_call:
        gpt4_client.call(messages)
        kwargs = mock_call.call_args[1]
        assert "temperature" in kwargs
        assert kwargs["temperature"] == 0.7


def test_call_applies_cache_prefix(client):
    cached = [LLMMessage(role="user", content="Cached context", cache=True)]
    dynamic = [LLMMessage(role="user", content="New question")]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Answer"
    mock_response.model = "claude-haiku-4-5"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    with patch("aspectcoder.llm.client.litellm.completion", return_value=mock_response) as mock_call:
        client.call(dynamic, cached_prefix=cached)
        call_kwargs = mock_call.call_args
        messages_sent = call_kwargs[1]["messages"]
        assert len(messages_sent) == 2
        # Cached prefix is prepended — index 0 is the cached message
        assert messages_sent[0]["content"][0]["cache_control"] == {"type": "ephemeral"}
        assert messages_sent[0]["content"][0]["text"] == "Cached context"
        # Dynamic message is a plain string, not wrapped in a content block
        assert messages_sent[1]["content"] == "New question"


def test_empty_content_raises_valueerror(client):
    messages = [LLMMessage(role="user", content="Hi")]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = ""
    mock_response.model = "gpt-5-mini"
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 2048

    with patch("aspectcoder.llm.client.litellm.completion", return_value=mock_response):
        with pytest.raises(ValueError, match="empty content"):
            client.call(messages)


def test_none_content_raises_valueerror(client):
    messages = [LLMMessage(role="user", content="Hi")]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = None
    mock_response.model = "gpt-5-mini"
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 2048

    with patch("aspectcoder.llm.client.litellm.completion", return_value=mock_response):
        with pytest.raises(ValueError, match="empty content"):
            client.call(messages)
