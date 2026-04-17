from __future__ import annotations
import re
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from aspectcoder.config import ModelConfig
from aspectcoder.llm.client import LLMClient, LLMMessage

InputT  = TypeVar("InputT")
OutputT = TypeVar("OutputT")

# Retries after the first attempt; total attempts = MAX_PARSE_RETRIES + 1
MAX_PARSE_RETRIES = 2

_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _strip_fences(raw: str) -> str:
    m = _FENCE_RE.match(raw.strip())
    return m.group(1).strip() if m else raw


class BaseAgent(ABC, Generic[InputT, OutputT]):
    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = LLMClient(config)
        self.last_needs_human: bool = False

    def run(self, input: InputT, *, cached_prefix: list[LLMMessage] | None = None) -> OutputT:
        self.last_needs_human = False
        messages = self.build_messages(input)
        last_error: Exception | None = None

        for attempt in range(MAX_PARSE_RETRIES + 1):
            response = self.client.call(messages, cached_prefix=cached_prefix)
            try:
                output = self.parse_output(_strip_fences(response.content))
                self.last_needs_human = getattr(output, "needs_human", False)
                return output
            except Exception as e:
                last_error = e
                messages = messages + [
                    LLMMessage(role="assistant", content=response.content),
                    LLMMessage(role="user", content=f"That response could not be parsed. Error: {e}. Please respond with valid JSON only."),
                ]

        raise ValueError(f"Agent failed to produce parseable output after {MAX_PARSE_RETRIES + 1} attempts. Last error: {last_error}")

    @abstractmethod
    def build_messages(self, input: InputT) -> list[dict]:
        """Return the messages list to send to the LLM."""

    @abstractmethod
    def parse_output(self, raw: str) -> OutputT:
        """Parse the raw LLM string response into the typed output."""
