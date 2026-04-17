from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR    = "major"
    MINOR    = "minor"


class Issue(BaseModel):
    severity: IssueSeverity
    description: str
    location: str = ""        # "file.c:42" or empty if non-local
    suggestion: str


class ReviewerType(str, Enum):
    FUNCTIONAL  = "functional"
    SECURITY    = "security"
    PERFORMANCE = "performance"


class PlanVerdict(BaseModel):
    pass_: bool
    confidence: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    needs_human: bool = False


class ReviewVerdict(BaseModel):
    reviewer: ReviewerType
    pass_: bool
    confidence: float = Field(ge=0.0, le=1.0)
    issues: list[Issue] = Field(default_factory=list)
    approach_wrong: bool = False
    needs_human: bool = False
