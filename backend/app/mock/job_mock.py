import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.enums import ActivityEventType, ActivitySeverity, JobStatus, JobTargetType
from app.models.job import Job
from app.services.activity_service import log_activity

ACTION_LOGS: dict[str, list[str]] = {
    "health-check": [
        "Checking SSH connectivity...",
        "Gathering system information...",
        "Collecting CPU, RAM, and disk metrics...",
        "Running health check probes...",
        "Task completed successfully.",
    ],
    "update-packages": [
        "Connecting to node via SSH...",
        "Updating package index (apt update)...",
        "Checking for available upgrades...",
        "Applying security patches...",
        "Package update completed.",
    ],
    "restart-docker": [
        "Connecting to node via SSH...",
        "Checking Docker daemon status...",
        "Stopping Docker service...",
        "Starting Docker service...",
        "Verifying container runtime...",
        "Docker restarted successfully.",
    ],
    "install-node-exporter": [
        "Connecting to node via SSH...",
        "Downloading node_exporter binary...",
        "Creating systemd service unit...",
        "Enabling and starting node_exporter...",
        "Node Exporter installed on port 9100.",
    ],
    "run-backup": [
        "Connecting to node via SSH...",
        "Identifying backup targets...",
        "Creating compressed archive...",
        "Uploading to backup storage...",
        "Backup completed successfully.",
    ],
}

DEFAULT_LOGS = [
    "Initializing automation runner...",
    "Checking SSH connectivity...",
    "Gathering system information...",
    "Running selected automation task...",
    "Task completed successfully.",
]


def _generate_job_id() -> str:
    return f"job-{uuid.uuid4().hex[:8]}"


def create_and_run_job(
    db: Session,
    action_name: str,
    target_type: str,
    target_id: uuid.UUID,
    created_by: str = "system",
    fail_chance: float = 0.1,
) -> Job:
    now = datetime.utcnow()
    job = Job(
        job_id=_generate_job_id(),
        action_name=action_name,
        target_type=target_type,
        target_id=target_id,
        status=JobStatus.PENDING.value,
        created_by=created_by,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    log_activity(
        db,
        event_type=ActivityEventType.JOB_STARTED.value,
        message=f"Job {job.job_id} started: {action_name}",
        severity=ActivitySeverity.INFO.value,
        related_entity_type=target_type,
        related_entity_id=target_id,
    )

    job.status = JobStatus.RUNNING.value
    job.started_at = now + timedelta(seconds=1)
    db.commit()

    logs = ACTION_LOGS.get(action_name, DEFAULT_LOGS)
    success = random.random() > fail_chance

    if success:
        job.status = JobStatus.SUCCESS.value
        job.output_log = "\n".join(logs)
        job.error_log = None
        severity = ActivitySeverity.INFO.value
        message = f"Job {job.job_id} completed successfully: {action_name}"
    else:
        job.status = JobStatus.FAILED.value
        job.output_log = "\n".join(logs[:-1])
        job.error_log = "Error: Task failed during execution. Check target connectivity."
        severity = ActivitySeverity.ERROR.value
        message = f"Job {job.job_id} failed: {action_name}"

    job.finished_at = job.started_at + timedelta(seconds=random.randint(2, 8))
    db.commit()
    db.refresh(job)

    log_activity(
        db,
        event_type=ActivityEventType.JOB_COMPLETED.value,
        message=message,
        severity=severity,
        related_entity_type=target_type,
        related_entity_id=target_id,
    )
    return job


def rerun_job(db: Session, job: Job) -> Job:
    return create_and_run_job(
        db,
        action_name=job.action_name,
        target_type=job.target_type,
        target_id=job.target_id,
        created_by=job.created_by,
    )
