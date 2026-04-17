from __future__ import annotations
from pydantic import BaseModel, Field


class Subtask(BaseModel):
    id: str
    description: str
    target_file: str
    language: str                    # "python" | "c" | "cpp" | "javascript"
    dependencies: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    task_id: str
    task_description: str
    approach: str
    subtasks: list[Subtask]
    target_files: list[str]
    primary_language: str
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human: bool = False
