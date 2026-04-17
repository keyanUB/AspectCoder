from __future__ import annotations
from enum import Enum
from pathlib import Path

from aspectcoder.agents.reviewers.base import BaseReviewerAgent
from aspectcoder.agents.inputs import ReviewInput
from aspectcoder.models.verdict import ReviewVerdict
from aspectcoder.config import ModelConfig
from aspectcoder.llm.client import LLMMessage

_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"


def _load(filename: str) -> str:
    return (_KNOWLEDGE_DIR / filename).read_text()


class SecurityLevel(str, Enum):
    BASIC    = "basic"
    STANDARD = "standard"
    STRICT   = "strict"


_FOCUS: dict[SecurityLevel, str] = {
    SecurityLevel.BASIC: (
        "obvious security vulnerabilities only: hardcoded credentials, SQL/command injection, "
        "path traversal, XSS, and clear input-validation gaps. "
        "Focus on high-severity, easy-to-spot issues."
    ),
    SecurityLevel.STANDARD: (
        "security vulnerabilities based on the CWE Top 25 Most Dangerous Software Weaknesses "
        "provided in the reference below. Check the code against every item in the list."
    ),
    SecurityLevel.STRICT: (
        "security vulnerabilities. Check the code against every item in the CWE Top 25 "
        "and verify it does not violate any OWASP Secure Coding Practice provided in the "
        "references below."
    ),
}


class SecurityReviewerAgent(BaseReviewerAgent):
    reviewer_name = "security"

    def __init__(self, config: ModelConfig, level: SecurityLevel = SecurityLevel.STANDARD):
        super().__init__(config=config)
        self.level = level
        self._cached_prefix: list[LLMMessage] | None = self._build_prefix()

    def _build_prefix(self) -> list[LLMMessage] | None:
        if self.level == SecurityLevel.BASIC:
            return None
        messages: list[LLMMessage] = []
        messages.append(LLMMessage(
            role="user",
            content=f"# Reference: CWE Top 25\n\n{_load('cwe_top25.md')}",
            cache=True,
        ))
        if self.level == SecurityLevel.STRICT:
            messages.append(LLMMessage(
                role="user",
                content=f"# Reference: OWASP Secure Coding Practices\n\n{_load('owasp_scp.md')}",
                cache=True,
            ))
        return messages

    @property
    def reviewer_focus(self) -> str:
        return _FOCUS[self.level]

    def run(self, input: ReviewInput) -> ReviewVerdict:
        return super().run(input, cached_prefix=self._cached_prefix)
