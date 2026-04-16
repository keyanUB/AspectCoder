from __future__ import annotations
from dataclasses import dataclass
import litellm
from mycoder.config import ModelConfig


@dataclass
class LLMMessage:
    role: str           # "system" | "user" | "assistant"
    content: str
    cache: bool = False  # mark this message for prompt caching


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int]


class LLMClient:
    def __init__(self, config: ModelConfig):
        self.config = config

    def call(
        self,
        messages: list[LLMMessage],
        *,
        cached_prefix: list[LLMMessage] | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        all_messages = list(cached_prefix or []) + list(messages)
        litellm_messages = [
            self._to_litellm_message(m) for m in all_messages
        ]

        kwargs: dict = dict(
            model=self.config.model,
            messages=litellm_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        if response_format:
            kwargs["response_format"] = response_format

        result = litellm.completion(**kwargs)

        return LLMResponse(
            content=result.choices[0].message.content,
            model=result.model,
            usage={
                "prompt_tokens": result.usage.prompt_tokens or 0,
                "completion_tokens": result.usage.completion_tokens or 0,
            },
        )

    def _to_litellm_message(self, msg: LLMMessage) -> dict:
        m: dict = {"role": msg.role, "content": msg.content}
        if msg.cache:
            # Anthropic prompt caching: attach cache_control to content block
            m["content"] = [
                {
                    "type": "text",
                    "text": msg.content,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        return m
