import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.custom_playbook import CustomPlaybook
from app.models.node import Node

PLAYBOOKS_DIR = Path(__file__).resolve().parent.parent / "ansible" / "playbooks"


@dataclass
class JobActionInfo:
    name: str
    label: str
    description: str
    requires_sudo: bool
    timeout_seconds: int
    source: str = "builtin"
    custom_id: UUID | None = None
    playbook_content: str | None = None


@dataclass
class AnsibleRunResult:
    success: bool
    stdout: str
    stderr: str
    runner: str
    error: str | None = None


BUILTIN_ACTIONS: list[JobActionInfo] = [
    JobActionInfo(
        name="health-check",
        label="Run Health Check",
        description="Gather uptime, memory, and disk usage from the node.",
        requires_sudo=False,
        timeout_seconds=120,
    ),
    JobActionInfo(
        name="update-packages",
        label="Update Packages",
        description="Update system packages via apt (Debian/Ubuntu) or dnf (RHEL). Requires passwordless sudo.",
        requires_sudo=True,
        timeout_seconds=600,
    ),
    JobActionInfo(
        name="restart-docker",
        label="Restart Docker",
        description="Restart the Docker daemon and verify it is active. Requires passwordless sudo.",
        requires_sudo=True,
        timeout_seconds=120,
    ),
    JobActionInfo(
        name="install-node-exporter",
        label="Install Node Exporter",
        description="Download and install Prometheus node_exporter as a systemd service.",
        requires_sudo=True,
        timeout_seconds=300,
    ),
    JobActionInfo(
        name="run-backup",
        label="Run Backup",
        description="Create a compressed archive of /etc and /home under /tmp.",
        requires_sudo=True,
        timeout_seconds=300,
    ),
]

BUILTIN_ACTION_NAMES = {action.name for action in BUILTIN_ACTIONS}
ACTION_PLAYBOOKS = {action.name: f"{action.name}.yml" for action in BUILTIN_ACTIONS}


def is_ansible_available() -> bool:
    return shutil.which("ansible-playbook") is not None


def _custom_to_action(row: CustomPlaybook) -> JobActionInfo:
    return JobActionInfo(
        name=row.name,
        label=row.label,
        description=row.description or f"Custom playbook: {row.name}",
        requires_sudo=row.requires_sudo,
        timeout_seconds=row.timeout_seconds,
        source="custom",
        custom_id=row.id,
        playbook_content=row.playbook_content,
    )


def get_action_catalog(db: Session | None = None) -> list[JobActionInfo]:
    actions = list(BUILTIN_ACTIONS)
    if db is not None:
        custom_rows = db.query(CustomPlaybook).order_by(CustomPlaybook.name).all()
        actions.extend(_custom_to_action(row) for row in custom_rows)
    return actions


def get_action_info(db: Session | None, action_name: str) -> JobActionInfo | None:
    for action in BUILTIN_ACTIONS:
        if action.name == action_name:
            return action
    if db is None:
        return None
    row = db.query(CustomPlaybook).filter(CustomPlaybook.name == action_name).first()
    if row:
        return _custom_to_action(row)
    return None


def _friendly_error(stderr: str, stdout: str) -> str | None:
    combined = f"{stderr}\n{stdout}".lower()
    if "sudo: a password is required" in combined or "missing sudo password" in combined:
        return (
            "Sudo password required. Configure passwordless sudo for this user on the target node "
            "(NOPASSWD in sudoers) or run actions that do not require elevation."
        )
    if "connection refused" in combined or "no route to host" in combined:
        return "SSH connection to the node failed."
    if "permission denied (publickey" in combined:
        return "SSH authentication failed. Verify SSH credentials in Settings and authorized_keys on the node."
    if "could not find or access" in combined and "docker" in combined:
        return "Docker service not found on this node."
    return None


def run_ansible_action(
    node: Node,
    username: str,
    private_key: str,
    action_name: str,
    db: Session | None = None,
) -> AnsibleRunResult:
    action = get_action_info(db, action_name)
    if not action:
        return AnsibleRunResult(
            success=False,
            stdout="",
            stderr="",
            runner="ansible",
            error=f"Unknown action: {action_name}",
        )

    if not is_ansible_available():
        return AnsibleRunResult(
            success=False,
            stdout="",
            stderr="",
            runner="ansible",
            error="ansible-playbook is not installed in the OpsDeck backend container",
        )

    playbook_path: Path | None = None
    temp_playbook_path: str | None = None

    if action.playbook_content:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yml") as playbook_file:
            playbook_file.write(action.playbook_content)
            temp_playbook_path = playbook_file.name
            playbook_path = Path(temp_playbook_path)
    else:
        playbook_path = PLAYBOOKS_DIR / ACTION_PLAYBOOKS[action_name]
        if not playbook_path.exists():
            return AnsibleRunResult(
                success=False,
                stdout="",
                stderr="",
                runner="ansible",
                error=f"Playbook not found: {playbook_path.name}",
            )

    with tempfile.NamedTemporaryFile("w", delete=False, suffix="_opsdeck_key") as key_file:
        # OpenSSH requires a trailing newline; Paramiko tolerates its absence.
        key_file.write(private_key.strip() + "\n")
        key_path = key_file.name
    os.chmod(key_path, 0o600)

    inventory_content = (
        "[all]\n"
        f"opsdeck_target ansible_host={node.ip_address} "
        f"ansible_user={username} ansible_port={node.ssh_port}\n"
    )
    with tempfile.NamedTemporaryFile("w", delete=False, suffix="_opsdeck_inventory") as inv_file:
        inv_file.write(inventory_content)
        inventory_path = inv_file.name

    try:
        cmd = [
            "ansible-playbook",
            str(playbook_path),
            "-i",
            inventory_path,
            "--private-key",
            key_path,
            "--ssh-common-args",
            "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null",
        ]
        if action.requires_sudo:
            cmd.extend(["--become", "-e", "ansible_become_flags='-n'"])

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=action.timeout_seconds,
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        success = proc.returncode == 0
        error = None if success else _friendly_error(stderr, stdout)
        if not success and not error:
            error = stderr or stdout or f"ansible-playbook exited with code {proc.returncode}"

        return AnsibleRunResult(
            success=success,
            stdout=stdout,
            stderr=stderr,
            runner="ansible",
            error=error,
        )
    except subprocess.TimeoutExpired:
        return AnsibleRunResult(
            success=False,
            stdout="",
            stderr="",
            runner="ansible",
            error=f"Action timed out after {action.timeout_seconds}s",
        )
    finally:
        for path in (key_path, inventory_path, temp_playbook_path):
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass
