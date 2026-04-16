from datetime import datetime, timezone
from mycoder.models.job import JobStatus, JobState

def test_job_status_values():
    assert JobStatus.PENDING  == "pending"
    assert JobStatus.RUNNING  == "running"
    assert JobStatus.WAITING  == "waiting"
    assert JobStatus.DONE     == "done"
    assert JobStatus.FAILED   == "failed"

def test_job_state_defaults():
    now = datetime.now(timezone.utc)
    state = JobState(
        job_id="job-abc123",
        task_description="Add binary_search to utils.c",
        status=JobStatus.PENDING,
        current_version=0,
        created_at=now,
        updated_at=now,
    )
    assert state.verifier_retries == 0
    assert state.regen_retries == 0
    assert state.replan_retries == 0

def test_job_state_serialises():
    now = datetime.now(timezone.utc)
    state = JobState(
        job_id="job-abc123",
        task_description="task",
        status=JobStatus.RUNNING,
        current_version=1,
        created_at=now,
        updated_at=now,
    )
    data = state.model_dump()
    restored = JobState.model_validate(data)
    assert restored.job_id == "job-abc123"
    assert restored.status == JobStatus.RUNNING
