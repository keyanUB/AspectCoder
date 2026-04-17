from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    DONE    = "done"
    FAILED  = "failed"


class VerdictRecord(BaseModel):
    version: int
    reviewer: str
    pass_: bool
    issues: list[str] = Field(default_factory=list)


class JobState(BaseModel):
    job_id: str
    task_description: str
    status: JobStatus
    current_version: int
    verifier_retries: int = 0
    regen_retries: int = 0
    replan_retries: int = 0
    created_at: datetime
    updated_at: datetime
    verdicts: list[VerdictRecord] = Field(default_factory=list)
