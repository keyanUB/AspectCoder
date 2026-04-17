from __future__ import annotations
from pydantic import BaseModel, Field


class GeneratedCode(BaseModel):
    subtask_id: str
    language: str
    file_path: str
    code: str
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human: bool = False


class GenerationResult(BaseModel):
    subtasks: list[GeneratedCode]
    needs_human: bool = False
