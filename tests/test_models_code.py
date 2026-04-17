import pytest
from aspectcoder.models.code import GeneratedCode

def test_generated_code_valid():
    gc = GeneratedCode(
        subtask_id="subtask-1",
        language="c",
        file_path="src/utils.c",
        code="int binary_search(int *arr, int len, int target) { return -1; }",
        explanation="Stub implementation — bounds checking added in next step.",
        confidence=0.85,
    )
    assert gc.subtask_id == "subtask-1"
    assert gc.needs_human is False

def test_generated_code_low_confidence_does_not_auto_set_needs_human():
    gc = GeneratedCode(
        subtask_id="subtask-1",
        language="python",
        file_path="src/utils.py",
        code="def search(): pass",
        explanation="Incomplete.",
        confidence=0.2,
    )
    assert gc.needs_human is False

def test_generated_code_serialises():
    gc = GeneratedCode(
        subtask_id="subtask-1",
        language="javascript",
        file_path="src/utils.js",
        code="function search() {}",
        explanation="Empty stub.",
        confidence=0.5,
    )
    data = gc.model_dump()
    restored = GeneratedCode.model_validate(data)
    assert restored.language == "javascript"
