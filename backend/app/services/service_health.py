import socket
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from sqlalchemy.orm import Session

from app.models.enums import (
    ActivityEventType,
    ActivitySeverity,
    HealthCheckStatus,
    HealthCheckTargetType,
    ServiceProtocol,
    ServiceStatus,
)
from app.models.health_check import HealthCheck
from app.models.node import Node
from app.models.service import Service
from app.services.activity_service import log_activity

HTTP_TIMEOUT_S = 10.0
TCP_TIMEOUT_S = 5.0
SLOW_RESPONSE_MS = 2000


@dataclass
class ProbeResult:
    status: str
    response_time_ms: int | None
    message: str


def _service_status_from_health(status: str) -> str:
    mapping = {
        HealthCheckStatus.SUCCESS.value: ServiceStatus.UP.value,
        HealthCheckStatus.WARNING.value: ServiceStatus.WARNING.value,
        HealthCheckStatus.FAILED.value: ServiceStatus.DOWN.value,
    }
    return mapping.get(status, ServiceStatus.UNKNOWN.value)


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _resolve_http_url(service: Service, node: Node) -> str | None:
    if service.protocol == ServiceProtocol.TCP.value:
        return None

    protocol = service.protocol if service.protocol in (ServiceProtocol.HTTP.value, ServiceProtocol.HTTPS.value) else ServiceProtocol.HTTP.value
    host = node.ip_address
    port = service.port
    path = "/"

    if service.url:
        parsed = urlparse(service.url)
        if parsed.scheme == ServiceProtocol.TCP.value:
            return None
        if parsed.scheme in (ServiceProtocol.HTTP.value, ServiceProtocol.HTTPS.value):
            protocol = parsed.scheme
        if parsed.port:
            port = parsed.port
        if parsed.path:
            path = parsed.path

    if port is None:
        port = 443 if protocol == ServiceProtocol.HTTPS.value else 80

    default_port = 443 if protocol == ServiceProtocol.HTTPS.value else 80
    netloc = host if port == default_port else f"{host}:{port}"
    return urlunparse((protocol, netloc, path, "", "", ""))


def _resolve_tcp_target(service: Service, node: Node) -> tuple[str, int] | None:
    port = service.port
    if service.url:
        parsed = urlparse(service.url)
        if parsed.scheme == ServiceProtocol.TCP.value and parsed.port:
            port = parsed.port

    if not port:
        return None
    return node.ip_address, port


def _http_status_from_code(code: int, elapsed_ms: int) -> tuple[str, str]:
    if code == 503:
        return HealthCheckStatus.WARNING.value, f"HTTP 503 Service Unavailable ({elapsed_ms}ms)."
    if code >= 500:
        return HealthCheckStatus.FAILED.value, f"HTTP {code} server error ({elapsed_ms}ms)."
    if code >= 400:
        return HealthCheckStatus.WARNING.value, f"HTTP {code} client error ({elapsed_ms}ms)."
    status = HealthCheckStatus.SUCCESS.value
    message = f"HTTP {code} OK ({elapsed_ms}ms)."
    if elapsed_ms >= SLOW_RESPONSE_MS:
        status = HealthCheckStatus.WARNING.value
        message = f"HTTP {code} OK but slow response ({elapsed_ms}ms)."
    return status, message


def _check_http(url: str) -> ProbeResult:
    start = time.perf_counter()
    request = urllib.request.Request(url, method="GET")
    context = _ssl_context() if url.startswith("https://") else None

    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S, context=context) as response:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            status, message = _http_status_from_code(response.status, elapsed_ms)
            return ProbeResult(status=status, response_time_ms=elapsed_ms, message=message)
    except urllib.error.HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        status, message = _http_status_from_code(exc.code, elapsed_ms)
        return ProbeResult(
            status=status,
            response_time_ms=elapsed_ms if status != HealthCheckStatus.FAILED.value else None,
            message=message,
        )
    except Exception as exc:
        return ProbeResult(
            status=HealthCheckStatus.FAILED.value,
            response_time_ms=None,
            message=f"HTTP request to {url} failed: {exc}",
        )


def _check_tcp(host: str, port: int) -> ProbeResult:
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=TCP_TIMEOUT_S):
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            status = HealthCheckStatus.SUCCESS.value
            message = f"TCP connection to {host}:{port} succeeded ({elapsed_ms}ms)."
            if elapsed_ms >= SLOW_RESPONSE_MS:
                status = HealthCheckStatus.WARNING.value
                message = f"TCP connection to {host}:{port} succeeded but slow ({elapsed_ms}ms)."
            return ProbeResult(status=status, response_time_ms=elapsed_ms, message=message)
    except Exception as exc:
        return ProbeResult(
            status=HealthCheckStatus.FAILED.value,
            response_time_ms=None,
            message=f"TCP connection to {host}:{port} failed: {exc}",
        )


def probe_service(service: Service, node: Node) -> ProbeResult | None:
    if not node.ip_address:
        return None

    if service.protocol == ServiceProtocol.TCP.value:
        target = _resolve_tcp_target(service, node)
        if not target:
            return None
        host, port = target
        return _check_tcp(host, port)

    url = _resolve_http_url(service, node)
    if not url:
        return None
    return _check_http(url)


def _persist_service_health_check(db: Session, service: Service, result: ProbeResult) -> HealthCheck:
    old_status = service.status
    check = HealthCheck(
        target_type=HealthCheckTargetType.SERVICE.value,
        target_id=service.id,
        status=result.status,
        response_time_ms=result.response_time_ms,
        message=result.message,
        checked_at=datetime.utcnow(),
    )
    db.add(check)

    service.status = _service_status_from_health(result.status)
    service.last_checked_at = check.checked_at
    db.commit()
    db.refresh(check)

    if old_status != service.status:
        log_activity(
            db,
            event_type=ActivityEventType.SERVICE_STATUS_CHANGED.value,
            message=f"Service '{service.name}' status changed: {old_status} → {service.status}",
            severity=ActivitySeverity.WARNING.value
            if service.status in (ServiceStatus.DOWN.value, ServiceStatus.WARNING.value)
            else ActivitySeverity.INFO.value,
            related_entity_type="service",
            related_entity_id=service.id,
        )

    severity = ActivitySeverity.INFO.value
    if result.status == HealthCheckStatus.WARNING.value:
        severity = ActivitySeverity.WARNING.value
    elif result.status == HealthCheckStatus.FAILED.value:
        severity = ActivitySeverity.ERROR.value

    log_activity(
        db,
        event_type=ActivityEventType.HEALTH_CHECK_EXECUTED.value,
        message=f"Health check on service '{service.name}': {result.status}",
        severity=severity,
        related_entity_type="service",
        related_entity_id=service.id,
    )
    return check


def run_service_health_check(db: Session, service: Service) -> HealthCheck:
    node = db.query(Node).filter(Node.id == service.node_id).first()
    if node:
        result = probe_service(service, node)
        if result is not None:
            return _persist_service_health_check(db, service, result)

    from app.mock.health_check_mock import run_service_health_check as run_mock

    return run_mock(db, service)
