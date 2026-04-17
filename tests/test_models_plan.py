import pytest
from aspectcoder.models.plan import Subtask, Plan


def test_subtask_requires_fields():
    with pytest.raises(Exception):
        Subtask()  # missing required fields


def test_subtask_valid():
    s = Subtask(
        id="subtask-1",
        description="Implement binary_search in utils.c",
        target_file="src/utils.c",
        language="c",
        dependencies=[],
    )
    assert s.id == "subtask-1"
    assert s.language == "c"


def test_plan_valid():
    subtask = Subtask(
        id="subtask-1",
        description="Implement binary_search",
        target_file="src/utils.c",
        language="c",
        dependencies=[],
    )
    plan = Plan(
        task_id="job-abc123",
        task_description="Add binary_search to utils.c",
        approach="Add iterative binary search with bounds checking",
        subtasks=[subtask],
        target_files=["src/utils.c"],
        primary_language="c",
        confidence=0.92,
    )
    assert plan.confidence == 0.92
    assert plan.needs_human is False  # default


def test_plan_serialises_to_json():
    subtask = Subtask(
        id="subtask-1",
        description="Implement binary_search",
        target_file="src/utils.c",
        language="c",
        dependencies=[],
    )
    plan = Plan(
        task_id="job-abc123",
        task_description="Add binary_search to utils.c",
        approach="Iterative binary search",
        subtasks=[subtask],
        target_files=["src/utils.c"],
        primary_language="c",
        confidence=0.9,
    )
    data = plan.model_dump()
    restored = Plan.model_validate(data)
    assert restored.task_id == plan.task_id
