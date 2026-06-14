import logging
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.backup import NodeBackup
from app.models.enums import ActivityEventType, ActivitySeverity
from app.models.node import Node
from app.services.activity_service import log_activity
from app.services.backup_storage import delete_object, read_bytes, save_bytes, storage_type
from app.services.ssh_client import connect, resolve_node_ssh_user
from app.services.ssh_credentials import get_decrypted_private_key, is_ssh_configured

logger = logging.getLogger(__name__)

BACKUP_TIMEOUT_SECONDS = 600


@dataclass
class BackupRunResult:
    success: bool
    backup: NodeBackup | None = None
    message: str = ""
    error: str | None = None


@dataclass
class AutoBackupResult:
    nodes_attempted: int = 0
    nodes_succeeded: int = 0
    nodes_failed: int = 0
    skipped: bool = False
    summary: str = ""
    errors: list[str] | None = None


def _backup_filename(node: Node) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in node.name)
    return f"opsdeck-{safe_name}-{stamp}.tar.gz"


def _remote_backup_path(filename: str) -> str:
    return f"/tmp/{filename}"


def _create_remote_archive(
    node: Node,
    username: str,
    private_key: str,
    remote_path: str,
) -> tuple[bool, str]:
    command = (
        f"sudo -n tar czf {remote_path} -C / etc home 2>/dev/null "
        f"|| sudo -n tar czf {remote_path} -C / etc 2>/dev/null"
    )
    client = None
    try:
        client = connect(
            node.ip_address,
            node.ssh_port,
            username,
            private_key,
            timeout=30,
        )
        _, stdout, stderr = client.exec_command(command, timeout=BACKUP_TIMEOUT_SECONDS)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            return False, stderr.read().decode("utf-8", errors="replace") or f"tar exited {exit_code}"
        return True, stdout.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return False, str(exc)
    finally:
        if client:
            client.close()


def _fetch_remote_file(
    node: Node,
    username: str,
    private_key: str,
    remote_path: str,
) -> bytes:
    client = None
    try:
        client = connect(
            node.ip_address,
            node.ssh_port,
            username,
            private_key,
            timeout=30,
        )
        sftp = client.open_sftp()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as tmp:
            local_tmp = tmp.name
        try:
            sftp.get(remote_path, local_tmp)
            return Path(local_tmp).read_bytes()
        finally:
            Path(local_tmp).unlink(missing_ok=True)
    finally:
        if client:
            client.close()


def _remove_remote_file(
    node: Node,
    username: str,
    private_key: str,
    remote_path: str,
) -> None:
    client = None
    try:
        client = connect(
            node.ip_address,
            node.ssh_port,
            username,
            private_key,
            timeout=30,
        )
        client.exec_command(f"sudo -n rm -f {remote_path}", timeout=30)
    except Exception:
        logger.warning("Failed to remove remote backup %s on %s", remote_path, node.name)
    finally:
        if client:
            client.close()


def _upload_remote_file(
    node: Node,
    username: str,
    private_key: str,
    local_data: bytes,
    remote_path: str,
) -> None:
    client = None
    try:
        client = connect(
            node.ip_address,
            node.ssh_port,
            username,
            private_key,
            timeout=30,
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as tmp:
            tmp.write(local_data)
            local_tmp = tmp.name
        try:
            sftp = client.open_sftp()
            sftp.put(local_tmp, remote_path)
        finally:
            Path(local_tmp).unlink(missing_ok=True)
    finally:
        if client:
            client.close()


def _restore_remote_archive(
    node: Node,
    username: str,
    private_key: str,
    remote_path: str,
) -> tuple[bool, str]:
    command = f"sudo -n tar xzf {remote_path} -C /"
    client = None
    try:
        client = connect(
            node.ip_address,
            node.ssh_port,
            username,
            private_key,
            timeout=30,
        )
        _, stdout, stderr = client.exec_command(command, timeout=BACKUP_TIMEOUT_SECONDS)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            return False, stderr.read().decode("utf-8", errors="replace") or f"restore exited {exit_code}"
        return True, stdout.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return False, str(exc)
    finally:
        if client:
            client.close()


def list_node_backups(db: Session, node_id: uuid.UUID) -> list[NodeBackup]:
    return (
        db.query(NodeBackup)
        .filter(NodeBackup.node_id == node_id)
        .order_by(NodeBackup.created_at.desc())
        .all()
    )


def get_node_backup(db: Session, node_id: uuid.UUID, backup_id: uuid.UUID) -> NodeBackup | None:
    return (
        db.query(NodeBackup)
        .filter(NodeBackup.id == backup_id, NodeBackup.node_id == node_id)
        .first()
    )


def create_node_backup(db: Session, node: Node) -> BackupRunResult:
    if not is_ssh_configured(db):
        return BackupRunResult(success=False, error="SSH credentials not configured")

    creds = get_decrypted_private_key(db)
    if not creds:
        return BackupRunResult(success=False, error="SSH credentials not configured")

    global_user, private_key = creds
    username = resolve_node_ssh_user(node, global_user)
    filename = _backup_filename(node)
    remote_path = _remote_backup_path(filename)

    ok, output = _create_remote_archive(node, username, private_key, remote_path)
    if not ok:
        row = NodeBackup(
            node_id=node.id,
            filename=filename,
            storage_type=storage_type(),
            storage_path="",
            status="failed",
            error_message=output,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return BackupRunResult(success=False, backup=row, error=output)

    try:
        data = _fetch_remote_file(node, username, private_key, remote_path)
        stored_type, stored_path = save_bytes(data, node.name, filename)
        row = NodeBackup(
            node_id=node.id,
            filename=filename,
            storage_type=stored_type,
            storage_path=stored_path,
            size_bytes=len(data),
            status="completed",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        log_activity(
            db,
            event_type=ActivityEventType.JOB_COMPLETED.value,
            message=f"Backup saved for node '{node.name}' ({len(data)} bytes, {stored_type})",
            severity=ActivitySeverity.INFO.value,
            related_entity_type="node",
            related_entity_id=node.id,
        )
        return BackupRunResult(
            success=True,
            backup=row,
            message=f"Backup saved ({stored_type}, {len(data)} bytes)",
        )
    except Exception as exc:
        row = NodeBackup(
            node_id=node.id,
            filename=filename,
            storage_type=storage_type(),
            storage_path="",
            status="failed",
            error_message=str(exc),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return BackupRunResult(success=False, backup=row, error=str(exc))
    finally:
        _remove_remote_file(node, username, private_key, remote_path)


def restore_node_backup(db: Session, node: Node, backup: NodeBackup) -> BackupRunResult:
    if backup.status != "completed" or not backup.storage_path:
        return BackupRunResult(success=False, error="Backup is not restorable")

    if not is_ssh_configured(db):
        return BackupRunResult(success=False, error="SSH credentials not configured")

    creds = get_decrypted_private_key(db)
    if not creds:
        return BackupRunResult(success=False, error="SSH credentials not configured")

    global_user, private_key = creds
    username = resolve_node_ssh_user(node, global_user)
    remote_path = _remote_backup_path(backup.filename)

    try:
        data = read_bytes(backup.storage_path, backup.storage_type)
        _upload_remote_file(node, username, private_key, data, remote_path)
        ok, output = _restore_remote_archive(node, username, private_key, remote_path)
        if not ok:
            return BackupRunResult(success=False, error=output or "Restore failed")
        log_activity(
            db,
            event_type=ActivityEventType.JOB_COMPLETED.value,
            message=f"Restored backup '{backup.filename}' on node '{node.name}'",
            severity=ActivitySeverity.WARNING.value,
            related_entity_type="node",
            related_entity_id=node.id,
        )
        return BackupRunResult(success=True, message="Restore completed")
    except Exception as exc:
        return BackupRunResult(success=False, error=str(exc))
    finally:
        _remove_remote_file(node, username, private_key, remote_path)


def delete_node_backup(db: Session, backup: NodeBackup) -> None:
    if backup.storage_path and backup.status == "completed":
        try:
            delete_object(backup.storage_path, backup.storage_type)
        except Exception:
            logger.exception("Failed to delete backup object %s", backup.storage_path)
    db.delete(backup)
    db.commit()


def run_auto_backups(db: Session, *, force: bool = False) -> AutoBackupResult:
    from app.services.backup_settings_service import get_or_create_backup_settings, record_auto_backup_result

    settings_row = get_or_create_backup_settings(db)
    if not force and not settings_row.auto_backup_enabled:
        return AutoBackupResult(skipped=True, summary="Auto backup disabled")

    if not is_ssh_configured(db):
        return AutoBackupResult(skipped=True, summary="SSH credentials not configured")

    nodes = (
        db.query(Node)
        .filter(Node.auto_backup_enabled.is_(True))
        .order_by(Node.name)
        .all()
    )
    if not nodes:
        return AutoBackupResult(skipped=True, summary="No nodes with auto backup enabled")

    attempted = 0
    succeeded = 0
    failed = 0
    errors: list[str] = []

    for node in nodes:
        attempted += 1
        result = create_node_backup(db, node)
        if result.success:
            succeeded += 1
        else:
            failed += 1
            errors.append(f"{node.name}: {result.error or 'failed'}")

    summary = f"Auto backup: {succeeded}/{attempted} node(s) succeeded"
    if failed:
        summary += f", {failed} failed"

    from app.services.backup_settings_service import record_auto_backup_result

    record_auto_backup_result(db, summary)
    return AutoBackupResult(
        nodes_attempted=attempted,
        nodes_succeeded=succeeded,
        nodes_failed=failed,
        summary=summary,
        errors=errors or None,
    )
