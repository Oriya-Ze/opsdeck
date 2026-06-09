import json
import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.container import Container
from app.models.enums import ActivityEventType, ActivitySeverity, ContainerStatus
from app.models.node import Node
from app.services.activity_service import log_activity
from app.services.ssh_client import exec_command, resolve_node_ssh_user
from app.services.ssh_credentials import get_decrypted_private_key, is_ssh_configured

DOCKER_PS_CMD = (
    "docker ps -a --format '{{json .}}' 2>/dev/null "
    "|| sudo -n docker ps -a --format '{{json .}}' 2>/dev/null"
)

DOCKER_STATS_CMD = (
    "docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' 2>/dev/null "
    "|| sudo -n docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' 2>/dev/null"
)

DOCKER_RESTART_CMD = (
    "docker ps -aq | xargs -r docker inspect --format '{{.Name}}\t{{.RestartCount}}' 2>/dev/null "
    "|| docker ps -aq | xargs -r sudo -n docker inspect --format '{{.Name}}\t{{.RestartCount}}' 2>/dev/null"
)


@dataclass
class DockerContainerInfo:
    name: str
    image: str
    status: str
    ports: str | None
    restart_count: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0


def _map_docker_status(raw: str) -> str:
    lower = raw.lower()
    if lower.startswith("up") or "running" in lower:
        return ContainerStatus.RUNNING.value
    if "restarting" in lower:
        return ContainerStatus.RESTARTING.value
    if "dead" in lower or "removing" in lower:
        return ContainerStatus.FAILED.value
    if "exited" in lower or "created" in lower or "paused" in lower:
        return ContainerStatus.STOPPED.value
    return ContainerStatus.UNKNOWN.value


def _parse_cpu(perc: str) -> float:
    try:
        return float(perc.replace("%", "").strip())
    except ValueError:
        return 0.0


def _parse_memory_mb(usage: str) -> float:
    # e.g. "12.5MiB / 256MiB" or "1.2GiB / 4GiB"
    part = usage.split("/")[0].strip().upper()
    match = re.match(r"([\d.]+)\s*([KMG]I?B)", part)
    if not match:
        return 0.0
    value = float(match.group(1))
    unit = match.group(2)
    if unit.startswith("G"):
        return value * 1024
    if unit.startswith("M"):
        return value
    if unit.startswith("K"):
        return value / 1024
    return value


def _parse_ps_output(stdout: str) -> list[DockerContainerInfo]:
    containers: list[DockerContainerInfo] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = row.get("Names", "").lstrip("/")
        if not name:
            continue
        containers.append(
            DockerContainerInfo(
                name=name,
                image=row.get("Image", "unknown"),
                status=_map_docker_status(row.get("Status", "")),
                ports=row.get("Ports") or None,
            )
        )
    return containers


def _apply_stats(containers: list[DockerContainerInfo], stdout: str) -> None:
    by_name = {c.name: c for c in containers}
    for line in stdout.splitlines():
        parts = line.strip().split("\t")
        if len(parts) < 3:
            continue
        name = parts[0].lstrip("/")
        if name in by_name:
            by_name[name].cpu_usage = _parse_cpu(parts[1])
            by_name[name].memory_usage = _parse_memory_mb(parts[2])


def _apply_restart_counts(containers: list[DockerContainerInfo], stdout: str) -> None:
    by_name = {c.name: c for c in containers}
    for line in stdout.splitlines():
        parts = line.strip().split("\t")
        if len(parts) < 2:
            continue
        name = parts[0].lstrip("/")
        if name in by_name:
            try:
                by_name[name].restart_count = int(parts[1])
            except ValueError:
                pass


def fetch_containers_from_node(node: Node, db: Session) -> list[DockerContainerInfo]:
    if not is_ssh_configured(db):
        raise ValueError("SSH credentials not configured. Add them in Settings first.")

    creds = get_decrypted_private_key(db)
    if not creds:
        raise ValueError("SSH credentials not configured.")

    global_user, private_key = creds
    username = resolve_node_ssh_user(node, global_user)

    ps_result = exec_command(
        node.ip_address, node.ssh_port, username, private_key, DOCKER_PS_CMD, timeout=60
    )
    if not ps_result.success and not ps_result.stdout:
        err = ps_result.error or ps_result.stderr or "Failed to list Docker containers"
        if "not found" in err.lower() or "command not found" in err.lower():
            raise ValueError("Docker is not installed or not available on this node")
        raise ValueError(err)

    containers = _parse_ps_output(ps_result.stdout)
    if not containers and ps_result.stdout.strip() == "":
        check = exec_command(
            node.ip_address,
            node.ssh_port,
            username,
            private_key,
            "command -v docker >/dev/null 2>&1 && echo ok || echo missing",
        )
        if check.stdout.strip() == "missing":
            raise ValueError("Docker is not installed on this node")

    stats_result = exec_command(
        node.ip_address, node.ssh_port, username, private_key, DOCKER_STATS_CMD, timeout=60
    )
    if stats_result.stdout:
        _apply_stats(containers, stats_result.stdout)

    restart_result = exec_command(
        node.ip_address, node.ssh_port, username, private_key, DOCKER_RESTART_CMD, timeout=60
    )
    if restart_result.stdout:
        _apply_restart_counts(containers, restart_result.stdout)

    return containers


def sync_node_containers(db: Session, node: Node) -> tuple[list[Container], int, int]:
    """Sync containers for a node. Returns (containers, created_or_updated, removed)."""
    live = fetch_containers_from_node(node, db)
    live_names = {c.name for c in live}
    now = datetime.utcnow()

    existing = db.query(Container).filter(Container.node_id == node.id).all()
    existing_by_name = {c.name: c for c in existing}

    updated = 0
    for info in live:
        if info.name in existing_by_name:
            row = existing_by_name[info.name]
            old_status = row.status
            row.image = info.image
            row.status = info.status
            row.ports = info.ports
            row.restart_count = info.restart_count
            row.cpu_usage = info.cpu_usage
            row.memory_usage = info.memory_usage
            row.updated_at = now
            if old_status != info.status:
                log_activity(
                    db,
                    event_type=ActivityEventType.CONTAINER_STATUS_CHANGED.value,
                    message=f"Container '{info.name}' on '{node.name}': {old_status} → {info.status}",
                    severity=ActivitySeverity.WARNING.value
                    if info.status in ("failed", "stopped")
                    else ActivitySeverity.INFO.value,
                    related_entity_type="container",
                    related_entity_id=row.id,
                )
        else:
            row = Container(
                name=info.name,
                image=info.image,
                node_id=node.id,
                status=info.status,
                ports=info.ports,
                restart_count=info.restart_count,
                cpu_usage=info.cpu_usage,
                memory_usage=info.memory_usage,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
        updated += 1

    removed = 0
    for name, row in existing_by_name.items():
        if name not in live_names:
            db.delete(row)
            removed += 1

    db.commit()

    containers = (
        db.query(Container)
        .filter(Container.node_id == node.id)
        .order_by(Container.name)
        .all()
    )

    log_activity(
        db,
        event_type=ActivityEventType.CONTAINER_STATUS_CHANGED.value,
        message=f"Docker sync on '{node.name}': {len(live)} container(s) synced, {removed} removed",
        severity=ActivitySeverity.INFO.value,
        related_entity_type="node",
        related_entity_id=node.id,
    )

    return containers, updated, removed
