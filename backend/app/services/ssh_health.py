from datetime import datetime

from sqlalchemy.orm import Session

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
from app.services.ssh_client import exec_command, resolve_node_ssh_user
from app.services.ssh_credentials import get_decrypted_private_key, is_ssh_configured

METRICS_SCRIPT = r"""#!/bin/bash
cpu=$(top -bn1 | grep "Cpu(s)" | awk '{print $2+$4}' | cut -d. -f1)
[ -z "$cpu" ] && cpu=$(awk '/cpu /{u=$2+$4; t=$2+$4+$5+$6+$7+$8; if(t>0) print int(u*100/t); else print 0}' /proc/stat)
mem=$(free | awk '/Mem:/{printf "%.1f", $3/$2 * 100}')
disk=$(df / | awk 'NR==2 {gsub(/%/,""); print $5}')
uptime=$(uptime -p 2>/dev/null || uptime | awk -F'up ' '{print $2}' | awk -F',' '{print $1}')
echo "CPU=$cpu"
echo "MEM=$mem"
echo "DISK=$disk"
echo "UPTIME=$uptime"
"""


def _parse_metrics(output: str) -> dict[str, str | float]:
    metrics: dict[str, str | float] = {}
    for line in output.splitlines():
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip().upper()
            val = val.strip()
            if key in ("CPU", "MEM", "DISK"):
                try:
                    metrics[key] = float(val)
                except ValueError:
                    metrics[key] = 0.0
            elif key == "UPTIME":
                metrics[key] = val
    return metrics


def _status_from_metrics(cpu: float, mem: float, disk: float) -> str:
    if disk >= 90 or mem >= 95 or cpu >= 95:
        return HealthCheckStatus.FAILED.value
    if disk >= 80 or mem >= 85 or cpu >= 85:
        return HealthCheckStatus.WARNING.value
    return HealthCheckStatus.SUCCESS.value


def _node_status_from_health(status: str) -> str:
    mapping = {
        HealthCheckStatus.SUCCESS.value: NodeStatus.HEALTHY.value,
        HealthCheckStatus.WARNING.value: NodeStatus.WARNING.value,
        HealthCheckStatus.FAILED.value: NodeStatus.OFFLINE.value,
    }
    return mapping.get(status, NodeStatus.UNKNOWN.value)


def run_node_health_check_ssh(db: Session, node: Node) -> HealthCheck:
    creds = get_decrypted_private_key(db)
    if not creds:
        raise ValueError("SSH credentials not configured")

    global_user, private_key = creds
    username = resolve_node_ssh_user(node, global_user)

    ping = exec_command(
        node.ip_address,
        node.ssh_port,
        username,
        private_key,
        "echo connected",
    )

    if not ping.success:
        message = ping.error or ping.stderr or "SSH connection failed"
        check = HealthCheck(
            target_type=HealthCheckTargetType.NODE.value,
            target_id=node.id,
            status=HealthCheckStatus.FAILED.value,
            response_time_ms=ping.response_time_ms,
            message=message,
            checked_at=datetime.utcnow(),
        )
        db.add(check)
        node.status = NodeStatus.OFFLINE.value
        node.last_checked_at = check.checked_at
        db.commit()
        db.refresh(check)
        log_activity(
            db,
            event_type=ActivityEventType.HEALTH_CHECK_EXECUTED.value,
            message=f"Health check on node '{node.name}' failed: {message}",
            severity=ActivitySeverity.ERROR.value,
            related_entity_type="node",
            related_entity_id=node.id,
        )
        return check

    metrics_result = exec_command(
        node.ip_address,
        node.ssh_port,
        username,
        private_key,
        METRICS_SCRIPT,
    )

    metrics = _parse_metrics(metrics_result.stdout) if metrics_result.success else {}
    cpu = float(metrics.get("CPU", 0))
    mem = float(metrics.get("MEM", 0))
    disk = float(metrics.get("DISK", 0))
    uptime = str(metrics.get("UPTIME", "unknown"))

    status = _status_from_metrics(cpu, mem, disk)
    if not metrics_result.success:
        status = HealthCheckStatus.WARNING.value
        message = f"SSH OK but metrics collection failed: {metrics_result.stderr or metrics_result.error}"
    elif status == HealthCheckStatus.SUCCESS.value:
        message = f"SSH connectivity verified. CPU {cpu:.1f}%, RAM {mem:.1f}%, Disk {disk:.1f}%."
    elif status == HealthCheckStatus.WARNING.value:
        message = f"Node reachable with elevated usage. CPU {cpu:.1f}%, RAM {mem:.1f}%, Disk {disk:.1f}%."
    else:
        message = f"Critical resource usage. CPU {cpu:.1f}%, RAM {mem:.1f}%, Disk {disk:.1f}%."

    total_ms = ping.response_time_ms + metrics_result.response_time_ms

    check = HealthCheck(
        target_type=HealthCheckTargetType.NODE.value,
        target_id=node.id,
        status=status,
        response_time_ms=total_ms,
        message=message,
        checked_at=datetime.utcnow(),
    )
    db.add(check)

    node.status = _node_status_from_health(status)
    node.last_checked_at = check.checked_at
    if metrics:
        node.cpu_usage = cpu
        node.ram_usage = mem
        node.disk_usage = disk
        node.uptime = uptime
        # Try to detect OS from uname if we got it
        uname = exec_command(node.ip_address, node.ssh_port, username, private_key, "uname -srm")
        if uname.success and uname.stdout:
            node.os_name = uname.stdout[:100]

    db.commit()
    db.refresh(check)

    severity = ActivitySeverity.INFO.value
    if status == HealthCheckStatus.WARNING.value:
        severity = ActivitySeverity.WARNING.value
    elif status == HealthCheckStatus.FAILED.value:
        severity = ActivitySeverity.ERROR.value

    log_activity(
        db,
        event_type=ActivityEventType.HEALTH_CHECK_EXECUTED.value,
        message=f"Health check on node '{node.name}': {status}",
        severity=severity,
        related_entity_type="node",
        related_entity_id=node.id,
    )
    return check


def run_node_health_check(db: Session, node: Node) -> HealthCheck:
    """Run real SSH health check if configured, otherwise fall back to mock."""
    if is_ssh_configured(db):
        return run_node_health_check_ssh(db, node)
    from app.mock.health_check_mock import run_node_health_check as run_mock
    return run_mock(db, node)
