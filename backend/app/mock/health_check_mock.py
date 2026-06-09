import random
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.enums import (
    HealthCheckStatus,
    HealthCheckTargetType,
    NodeStatus,
    ServiceStatus,
)
from app.models.health_check import HealthCheck
from app.models.node import Node
from app.models.service import Service
from app.services.activity_service import log_activity
from app.models.enums import ActivityEventType, ActivitySeverity


def _random_response_time() -> int:
    return random.randint(12, 450)


def _node_status_from_health(status: str) -> str:
    mapping = {
        HealthCheckStatus.SUCCESS.value: NodeStatus.HEALTHY.value,
        HealthCheckStatus.WARNING.value: NodeStatus.WARNING.value,
        HealthCheckStatus.FAILED.value: NodeStatus.OFFLINE.value,
    }
    return mapping.get(status, NodeStatus.UNKNOWN.value)


def _service_status_from_health(status: str) -> str:
    mapping = {
        HealthCheckStatus.SUCCESS.value: ServiceStatus.UP.value,
        HealthCheckStatus.WARNING.value: ServiceStatus.WARNING.value,
        HealthCheckStatus.FAILED.value: ServiceStatus.DOWN.value,
    }
    return mapping.get(status, ServiceStatus.UNKNOWN.value)


NODE_MESSAGES = {
    HealthCheckStatus.SUCCESS.value: [
        "SSH connectivity verified. All metrics within normal range.",
        "Node responsive. CPU, RAM, and disk usage nominal.",
        "Health check passed. Uptime stable.",
    ],
    HealthCheckStatus.WARNING.value: [
        "Node reachable but disk usage above 80%.",
        "SSH OK but elevated CPU load detected.",
        "Warning: memory usage approaching threshold.",
    ],
    HealthCheckStatus.FAILED.value: [
        "SSH connection timed out after 30s.",
        "Node unreachable. Host may be offline.",
        "Authentication failed during health check.",
    ],
}

SERVICE_MESSAGES = {
    HealthCheckStatus.SUCCESS.value: [
        "HTTP 200 OK. Service responding normally.",
        "Endpoint reachable. Response time acceptable.",
        "Health endpoint returned healthy status.",
    ],
    HealthCheckStatus.WARNING.value: [
        "HTTP 503 returned. Service degraded.",
        "Slow response detected (>2s).",
        "TLS certificate expires within 7 days.",
    ],
    HealthCheckStatus.FAILED.value: [
        "Connection refused on target port.",
        "HTTP 500 Internal Server Error.",
        "Service unreachable from OpsDeck.",
    ],
}


def run_node_health_check(db: Session, node: Node) -> HealthCheck:
    weights = [0.7, 0.2, 0.1]
    status = random.choices(
        [HealthCheckStatus.SUCCESS.value, HealthCheckStatus.WARNING.value, HealthCheckStatus.FAILED.value],
        weights=weights,
    )[0]

    check = HealthCheck(
        target_type=HealthCheckTargetType.NODE.value,
        target_id=node.id,
        status=status,
        response_time_ms=_random_response_time() if status != HealthCheckStatus.FAILED.value else None,
        message=random.choice(NODE_MESSAGES[status]),
        checked_at=datetime.utcnow(),
    )
    db.add(check)

    node.status = _node_status_from_health(status)
    node.last_checked_at = check.checked_at
    if status == HealthCheckStatus.SUCCESS.value:
        node.cpu_usage = round(random.uniform(5, 45), 1)
        node.ram_usage = round(random.uniform(20, 65), 1)
        node.disk_usage = round(random.uniform(15, 55), 1)
        node.uptime = f"{random.randint(1, 90)}d {random.randint(0, 23)}h"

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


def run_service_health_check(db: Session, service: Service) -> HealthCheck:
    weights = [0.75, 0.15, 0.1]
    status = random.choices(
        [HealthCheckStatus.SUCCESS.value, HealthCheckStatus.WARNING.value, HealthCheckStatus.FAILED.value],
        weights=weights,
    )[0]

    old_status = service.status
    check = HealthCheck(
        target_type=HealthCheckTargetType.SERVICE.value,
        target_id=service.id,
        status=status,
        response_time_ms=_random_response_time() if status != HealthCheckStatus.FAILED.value else None,
        message=random.choice(SERVICE_MESSAGES[status]),
        checked_at=datetime.utcnow(),
    )
    db.add(check)

    service.status = _service_status_from_health(status)
    service.last_checked_at = check.checked_at
    db.commit()
    db.refresh(check)

    if old_status != service.status:
        log_activity(
            db,
            event_type=ActivityEventType.SERVICE_STATUS_CHANGED.value,
            message=f"Service '{service.name}' status changed: {old_status} → {service.status}",
            severity=ActivitySeverity.WARNING.value if service.status in ("down", "warning") else ActivitySeverity.INFO.value,
            related_entity_type="service",
            related_entity_id=service.id,
        )

    log_activity(
        db,
        event_type=ActivityEventType.HEALTH_CHECK_EXECUTED.value,
        message=f"Health check on service '{service.name}': {status}",
        severity=ActivitySeverity.INFO.value,
        related_entity_type="service",
        related_entity_id=service.id,
    )
    return check
