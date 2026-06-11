import asyncio
import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.enums import ActivityEventType, ActivitySeverity
from app.models.node import Node
from app.services.activity_service import log_activity
from app.services.docker_sync import sync_node_containers
from app.services.ssh_credentials import is_ssh_configured
from app.services.sync_settings_service import get_or_create_sync_settings, record_auto_sync_result

logger = logging.getLogger(__name__)

AUTO_SYNC_SSH_TIMEOUT = 15
_sync_lock = asyncio.Lock()


@dataclass
class NodeSyncResult:
    node_name: str
    success: bool
    synced: int = 0
    removed: int = 0
    error: str | None = None


@dataclass
class AutoSyncResult:
    nodes_attempted: int = 0
    nodes_succeeded: int = 0
    nodes_failed: int = 0
    total_containers: int = 0
    summary: str = ""
    errors: list[str] = field(default_factory=list)
    skipped: bool = False


def run_containers_auto_sync(db: Session, *, force: bool = False) -> AutoSyncResult:
    """Sync Docker containers on all eligible nodes."""
    result = AutoSyncResult()

    if not is_ssh_configured(db):
        result.summary = "Skipped: SSH credentials not configured"
        result.skipped = True
        return result

    settings = get_or_create_sync_settings(db)
    if not settings.containers_auto_sync_enabled and not force:
        result.summary = "Skipped: auto-sync disabled"
        result.skipped = True
        return result

    nodes = (
        db.query(Node)
        .filter(Node.auto_sync_containers.is_(True))
        .order_by(Node.name)
        .all()
    )
    result.nodes_attempted = len(nodes)

    if not nodes:
        result.summary = "No nodes enabled for container auto-sync"
        record_auto_sync_result(db, result.summary)
        return result

    node_results: list[NodeSyncResult] = []
    for node in nodes:
        try:
            containers, synced, removed = sync_node_containers(
                db, node, log_summary=False, ssh_timeout=AUTO_SYNC_SSH_TIMEOUT
            )
            node_results.append(
                NodeSyncResult(node.name, True, synced=synced, removed=removed)
            )
            result.nodes_succeeded += 1
            result.total_containers += len(containers)
        except Exception as exc:
            message = str(exc)
            logger.warning("Auto-sync failed for node %s: %s", node.name, message)
            node_results.append(NodeSyncResult(node.name, False, error=message))
            result.nodes_failed += 1
            result.errors.append(f"{node.name}: {message}")

    result.summary = (
        f"Auto-sync: {result.nodes_succeeded}/{result.nodes_attempted} node(s), "
        f"{result.total_containers} container(s)"
    )
    if result.nodes_failed:
        result.summary += f", {result.nodes_failed} failed"

    record_auto_sync_result(db, result.summary)

    if result.nodes_succeeded or result.nodes_failed:
        severity = ActivitySeverity.WARNING.value if result.nodes_failed else ActivitySeverity.INFO.value
        log_activity(
            db,
            event_type=ActivityEventType.CONTAINER_STATUS_CHANGED.value,
            message=result.summary,
            severity=severity,
            related_entity_type="settings",
            related_entity_id=None,
        )

    return result


def _run_with_db(*, force: bool) -> AutoSyncResult:
    db = SessionLocal()
    try:
        return run_containers_auto_sync(db, force=force)
    finally:
        db.close()


async def run_containers_auto_sync_async(*, force: bool = False) -> AutoSyncResult:
    """Run container auto-sync in a worker thread so the API stays responsive."""
    async with _sync_lock:
        return await asyncio.to_thread(_run_with_db, force=force)
