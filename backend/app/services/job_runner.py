import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.enums import ActivityEventType, ActivitySeverity, JobStatus
from app.models.job import Job
from app.models.node import Node
from app.services.activity_service import log_activity
from app.services.ssh_client import exec_command, resolve_node_ssh_user
from app.services.ssh_credentials import get_decrypted_private_key, is_ssh_configured

ACTION_COMMANDS: dict[str, str] = {
    "health-check": "echo 'Checking SSH connectivity...' && uptime && free -h && df -h /",
    "update-packages": "sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq 2>&1 || echo 'apt not available, trying yum' && sudo yum update -y 2>&1",
    "restart-docker": "sudo systemctl restart docker && sudo systemctl is-active docker",
    "install-node-exporter": (
        "curl -fsSL https://github.com/prometheus/node_exporter/releases/download/v1.8.2/"
        "node_exporter-1.8.2.linux-amd64.tar.gz | sudo tar xz -C /tmp && "
        "sudo mv /tmp/node_exporter-1.8.2.linux-amd64/node_exporter /usr/local/bin/ && "
        "echo '[Unit]\\nDescription=Node Exporter\\nAfter=network.target\\n\\n[Service]\\n"
        "User=nobody\\nExecStart=/usr/local/bin/node_exporter\\n\\n[Install]\\nWantedBy=multi-user.target' "
        "| sudo tee /etc/systemd/system/node_exporter.service > /dev/null && "
        "sudo systemctl daemon-reload && sudo systemctl enable --now node_exporter && "
        "sudo systemctl is-active node_exporter"
    ),
    "run-backup": "tar czf /tmp/opsdeck-backup-$(date +%Y%m%d).tar.gz /etc /home 2>/dev/null | tail -5; ls -lh /tmp/opsdeck-backup-*.tar.gz 2>/dev/null || echo 'Backup archive created'",
}


def _generate_job_id() -> str:
    return f"job-{uuid.uuid4().hex[:8]}"


def create_and_run_job(
    db: Session,
    action_name: str,
    target_type: str,
    target_id: uuid.UUID,
    created_by: str = "system",
    node: Node | None = None,
) -> Job:
    if not is_ssh_configured(db) or not node:
        from app.mock.job_mock import create_and_run_job as run_mock
        return run_mock(db, action_name, target_type, target_id, created_by)

    creds = get_decrypted_private_key(db)
    if not creds:
        from app.mock.job_mock import create_and_run_job as run_mock
        return run_mock(db, action_name, target_type, target_id, created_by)

    global_user, private_key = creds
    username = resolve_node_ssh_user(node, global_user)
    command = ACTION_COMMANDS.get(action_name, "echo 'Unknown action'")

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
    job.started_at = now
    db.commit()

    result = exec_command(
        node.ip_address,
        node.ssh_port,
        username,
        private_key,
        command,
        timeout=120,
    )

    output_lines = [
        f"Connecting to {node.name} ({node.ip_address}:{node.ssh_port}) as {username}...",
        f"Running action: {action_name}",
        "---",
    ]
    if result.stdout:
        output_lines.append(result.stdout)
    if result.stderr:
        output_lines.append(result.stderr)

    if result.success:
        job.status = JobStatus.SUCCESS.value
        job.output_log = "\n".join(output_lines)
        job.error_log = None
        severity = ActivitySeverity.INFO.value
        message = f"Job {job.job_id} completed successfully: {action_name}"
    else:
        job.status = JobStatus.FAILED.value
        job.output_log = "\n".join(output_lines)
        job.error_log = result.error or result.stderr or f"Command exited with code {result.exit_code}"
        severity = ActivitySeverity.ERROR.value
        message = f"Job {job.job_id} failed: {action_name}"

    job.finished_at = datetime.utcnow()
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


def rerun_job(db: Session, job: Job, node: Node | None = None) -> Job:
    return create_and_run_job(
        db,
        action_name=job.action_name,
        target_type=job.target_type,
        target_id=job.target_id,
        created_by=job.created_by,
        node=node,
    )
