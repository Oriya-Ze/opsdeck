import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.enums import (
    ActivityEventType,
    ActivitySeverity,
    HealthCheckStatus,
    HealthCheckTargetType,
    NodeStatus,
)
from app.models.health_check import HealthCheck
from app.models.node import Node
from app.services.activity_service import log_activity
from app.services.prometheus_api import PrometheusApiError, query_instant
from app.services.ssh_health import _node_status_from_health, _status_from_metrics

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 60
JOB_LABEL = 'job="node_exporter"'

PROM_QUERIES = {
    "up": f"up{{{JOB_LABEL}}}",
    "cpu": (
        f'100 - (avg by (node) (rate(node_cpu_seconds_total{{mode="idle", {JOB_LABEL}}}[5m])) * 100)'
    ),
    "mem": (
        f"(1 - node_memory_MemAvailable_bytes{{{JOB_LABEL}}} "
        f"/ node_memory_MemTotal_bytes{{{JOB_LABEL}}}) * 100"
    ),
    "disk": (
        f'(1 - node_filesystem_avail_bytes{{{JOB_LABEL}, mountpoint="/", fstype!="tmpfs"}} '
        f'/ node_filesystem_size_bytes{{{JOB_LABEL}, mountpoint="/", fstype!="tmpfs"}}) * 100'
    ),
    "uptime_sec": (
        f"node_time_seconds{{{JOB_LABEL}}} - node_boot_time_seconds{{{JOB_LABEL}}}"
    ),
}

_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None


@dataclass
class NodePrometheusMetrics:
    reachable: bool = False
    cpu: float | None = None
    mem: float | None = None
    disk: float | None = None
    uptime_seconds: float | None = None


@dataclass
class NodeSyncResult:
    nodes_attempted: int = 0
    nodes_synced: int = 0
    nodes_skipped: int = 0
    nodes_failed: int = 0
    summary: str = ""
    errors: list[str] = field(default_factory=list)


def _vector_by_node(result: dict) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in result.get("data", {}).get("result", []):
        metric = item.get("metric", {})
        node_name = metric.get("node") or metric.get("instance", "").split(":")[0]
        if not node_name:
            continue
        raw = item.get("value")
        if not raw or len(raw) < 2:
            continue
        try:
            values[node_name] = float(raw[1])
        except (TypeError, ValueError):
            continue
    return values


def _format_uptime(seconds: float) -> str:
    total = int(seconds)
    days, rem = divmod(total, 86400)
    hours, _ = divmod(rem, 3600)
    if days:
        return f"up {days} days, {hours} hours"
    if hours:
        return f"up {hours} hours"
    return f"up {max(rem // 60, 1)} minutes"


def fetch_node_metrics_from_prometheus() -> dict[str, NodePrometheusMetrics]:
    metrics_by_node: dict[str, NodePrometheusMetrics] = {}
    try:
        up_values = _vector_by_node(query_instant(PROM_QUERIES["up"]))
        cpu_values = _vector_by_node(query_instant(PROM_QUERIES["cpu"]))
        mem_values = _vector_by_node(query_instant(PROM_QUERIES["mem"]))
        disk_values = _vector_by_node(query_instant(PROM_QUERIES["disk"]))
        uptime_values = _vector_by_node(query_instant(PROM_QUERIES["uptime_sec"]))
    except PrometheusApiError as exc:
        raise PrometheusApiError(str(exc)) from exc

    all_nodes = set(up_values) | set(cpu_values) | set(mem_values) | set(disk_values)
    for name in all_nodes:
        up = up_values.get(name, 0)
        metrics_by_node[name] = NodePrometheusMetrics(
            reachable=up >= 1,
            cpu=cpu_values.get(name),
            mem=mem_values.get(name),
            disk=disk_values.get(name),
            uptime_seconds=uptime_values.get(name),
        )
    return metrics_by_node


def apply_prometheus_metrics_to_node(
    node: Node,
    metrics: NodePrometheusMetrics,
    *,
    create_health_check: bool = False,
    db: Session | None = None,
) -> bool:
    """Apply Prometheus metrics to a node. Returns True if metrics were applied."""
    if metrics.cpu is None and metrics.mem is None and not metrics.reachable:
        return False

    now = datetime.utcnow()
    cpu = metrics.cpu if metrics.cpu is not None else node.cpu_usage
    mem = metrics.mem if metrics.mem is not None else node.ram_usage
    disk = metrics.disk if metrics.disk is not None else node.disk_usage

    if not metrics.reachable:
        node.status = NodeStatus.OFFLINE.value
        message = "node_exporter unreachable (Prometheus)"
        health_status = HealthCheckStatus.FAILED.value
    else:
        health_status = _status_from_metrics(cpu, mem, disk)
        node.status = _node_status_from_health(health_status)
        message = (
            f"Prometheus sync: CPU {cpu:.1f}%, RAM {mem:.1f}%, Disk {disk:.1f}%."
        )

    node.cpu_usage = cpu
    node.ram_usage = mem
    node.disk_usage = disk
    if metrics.uptime_seconds is not None:
        node.uptime = _format_uptime(metrics.uptime_seconds)
    node.last_checked_at = now

    if create_health_check and db is not None:
        check = HealthCheck(
            target_type=HealthCheckTargetType.NODE.value,
            target_id=node.id,
            status=health_status,
            response_time_ms=0,
            message=message,
            checked_at=now,
        )
        db.add(check)

    return True


def sync_nodes_from_prometheus(db: Session) -> NodeSyncResult:
    result = NodeSyncResult()
    nodes = db.query(Node).order_by(Node.name).all()
    result.nodes_attempted = len(nodes)

    try:
        prom_metrics = fetch_node_metrics_from_prometheus()
    except PrometheusApiError as exc:
        result.summary = f"Prometheus node sync skipped: {exc}"
        return result

    for node in nodes:
        metrics = prom_metrics.get(node.name)
        if not metrics:
            result.nodes_skipped += 1
            continue
        try:
            if apply_prometheus_metrics_to_node(node, metrics):
                result.nodes_synced += 1
            else:
                result.nodes_skipped += 1
        except Exception as exc:
            result.nodes_failed += 1
            result.errors.append(f"{node.name}: {exc}")
            logger.warning("Prometheus sync failed for node %s: %s", node.name, exc)

    db.commit()

    result.summary = (
        f"Prometheus node sync: {result.nodes_synced}/{result.nodes_attempted} updated, "
        f"{result.nodes_skipped} without exporter"
    )
    if result.nodes_failed:
        result.summary += f", {result.nodes_failed} failed"

    if result.nodes_synced:
        log_activity(
            db,
            event_type=ActivityEventType.HEALTH_CHECK_EXECUTED.value,
            message=result.summary,
            severity=ActivitySeverity.INFO.value,
            related_entity_type="settings",
            related_entity_id=None,
        )

    return result


def sync_node_from_prometheus(db: Session, node: Node) -> HealthCheck | None:
    """Sync a single node from Prometheus. Returns HealthCheck if synced, None to use SSH fallback."""
    try:
        prom_metrics = fetch_node_metrics_from_prometheus()
    except PrometheusApiError:
        return None

    metrics = prom_metrics.get(node.name)
    if not metrics or (metrics.cpu is None and metrics.mem is None and not metrics.reachable):
        return None

    apply_prometheus_metrics_to_node(node, metrics, create_health_check=True, db=db)
    db.commit()

    check = (
        db.query(HealthCheck)
        .filter(
            HealthCheck.target_type == HealthCheckTargetType.NODE.value,
            HealthCheck.target_id == node.id,
        )
        .order_by(HealthCheck.checked_at.desc())
        .first()
    )
    if check:
        log_activity(
            db,
            event_type=ActivityEventType.HEALTH_CHECK_EXECUTED.value,
            message=f"Health check on node '{node.name}' via Prometheus: {check.status}",
            severity=ActivitySeverity.INFO.value,
            related_entity_type="node",
            related_entity_id=node.id,
        )
    return check


def _run_sync() -> None:
    db = SessionLocal()
    try:
        result = sync_nodes_from_prometheus(db)
        if result.nodes_synced:
            logger.info(result.summary)
    except Exception:
        logger.exception("Prometheus node sync loop error")
    finally:
        db.close()


async def _sync_loop() -> None:
    assert _stop_event is not None
    await asyncio.sleep(30)
    while not _stop_event.is_set():
        await asyncio.to_thread(_run_sync)
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=SYNC_INTERVAL_SECONDS)
            break
        except asyncio.TimeoutError:
            continue


def start_prometheus_node_sync() -> asyncio.Task:
    global _task, _stop_event
    _stop_event = asyncio.Event()
    _task = asyncio.create_task(_sync_loop(), name="prometheus-node-sync")
    logger.info("Prometheus node metrics sync started")
    return _task


async def stop_prometheus_node_sync() -> None:
    global _task, _stop_event
    if _stop_event:
        _stop_event.set()
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _task = None
    _stop_event = None
    logger.info("Prometheus node metrics sync stopped")
