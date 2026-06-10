import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.enums import ActivityEventType, ActivitySeverity, JobStatus
from app.models.job import Job
from app.models.node import Node
from app.services.activity_service import log_activity
from app.services.ansible_runner import get_action_info, is_ansible_available, run_ansible_action
from app.services.ssh_client import exec_command, resolve_node_ssh_user
from app.services.ssh_credentials import get_decrypted_private_key, is_ssh_configured

SHELL_FALLBACK_COMMANDS: dict[str, str] = {
    "health-check": "echo 'Checking SSH connectivity...' && uptime && free -h && df -h /",
    "update-packages": (
        "sudo -n DEBIAN_FRONTEND=noninteractive apt-get update -qq "
        "&& sudo -n DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq"
    ),
    "restart-docker": "sudo -n systemctl restart docker && sudo -n systemctl is-active docker",
    "install-node-exporter": (
        "curl -fsSL https://github.com/prometheus/node_exporter/releases/download/v1.8.2/"
        "node_exporter-1.8.2.linux-amd64.tar.gz | sudo -n tar xz -C /tmp && "
        "sudo -n mv /tmp/node_exporter-1.8.2.linux-amd64/node_exporter /usr/local/bin/ && "
        "sudo -n systemctl enable --now node_exporter 2>/dev/null || "
        "echo 'node_exporter install requires passwordless sudo'"
    ),
    "run-backup": (
        "sudo -n tar czf /tmp/opsdeck-backup-$(date +%Y%m%d).tar.gz /etc /home 2>/dev/null; "
        "ls -lh /tmp/opsdeck-backup-*.tar.gz 2>/dev/null || echo 'Backup requires passwordless sudo'"
    ),
}


def _generate_job_id() -> str:
    return f"job-{uuid.uuid4().hex[:8]}"


def _execute_action(
    db: Session,
    node: Node,
    username: str,
    private_key: str,
    action_name: str,
) -> tuple[bool, str, str | None, str]:
    """Returns success, output_log, error_log, runner label."""
    action = get_action_info(db, action_name)
    timeout = action.timeout_seconds if action else 120

    if is_ansible_available():
        result = run_ansible_action(node, username, private_key, action_name, db=db)
        playbook_label = f"{action_name}.yml" if action and action.source == "builtin" else f"custom:{action_name}"
        output_lines = [
            f"Runner: Ansible playbook ({playbook_label})",
            f"Target: {node.name} ({node.ip_address}:{node.ssh_port}) as {username}",
            "---",
        ]
        if result.stdout:
            output_lines.append(result.stdout)
        if result.stderr:
            output_lines.append(result.stderr)
        return result.success, "\n".join(output_lines), result.error, "ansible"

    if action and action.source == "custom":
        return False, "", "Custom playbooks require ansible-playbook in the OpsDeck backend container", "shell"

    command = SHELL_FALLBACK_COMMANDS.get(action_name)
    if not command:
        return False, "", f"Unknown action: {action_name}", "shell"

    result = exec_command(
        node.ip_address,
        node.ssh_port,
        username,
        private_key,
        command,
        timeout=timeout,
    )
    output_lines = [
        "Runner: shell fallback (ansible-playbook not available)",
        f"Target: {node.name} ({node.ip_address}:{node.ssh_port}) as {username}",
        f"Action: {action_name}",
        "---",
    ]
    if result.stdout:
        output_lines.append(result.stdout)
    if result.stderr:
        output_lines.append(result.stderr)

    error = None
    if not result.success:
        combined = f"{result.stderr}\n{result.stdout}".lower()
        if "sudo: a password is required" in combined:
            error = "Sudo password required. Configure passwordless sudo on the target node."
        else:
            error = result.error or result.stderr or f"Command exited with code {result.exit_code}"

    return result.success, "\n".join(output_lines), error, "shell"


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

    success, output_log, error_log, _runner = _execute_action(
        db, node, username, private_key, action_name
    )

    if success:
        job.status = JobStatus.SUCCESS.value
        job.output_log = output_log
        job.error_log = None
        severity = ActivitySeverity.INFO.value
        message = f"Job {job.job_id} completed successfully: {action_name}"
    else:
        job.status = JobStatus.FAILED.value
        job.output_log = output_log
        job.error_log = error_log
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
