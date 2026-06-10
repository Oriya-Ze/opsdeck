import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.enums import ActivityEventType, ActivitySeverity, WorkloadKind, WorkloadStatus
from app.models.node import Node
from app.models.workload import Workload
from app.services.activity_service import log_activity
from app.services.ssh_client import exec_command, resolve_node_ssh_user
from app.services.ssh_credentials import get_decrypted_private_key, is_ssh_configured

KUBECTL_RESOURCES = "deployments,statefulsets,daemonsets,pods,services,ingress"

KUBECTL_GET_CMD = (
    f"kubectl get {KUBECTL_RESOURCES} -A -o json 2>/dev/null "
    f"|| KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl get {KUBECTL_RESOURCES} -A -o json 2>/dev/null "
    f"|| sudo -n k3s kubectl get {KUBECTL_RESOURCES} -A -o json 2>/dev/null "
    f"|| k3s kubectl get {KUBECTL_RESOURCES} -A -o json 2>/dev/null"
)

KIND_MAP = {
    "Deployment": WorkloadKind.DEPLOYMENT.value,
    "StatefulSet": WorkloadKind.STATEFULSET.value,
    "DaemonSet": WorkloadKind.DAEMONSET.value,
    "Pod": WorkloadKind.POD.value,
    "Service": WorkloadKind.SERVICE.value,
    "Ingress": WorkloadKind.INGRESS.value,
}


@dataclass
class K8sWorkloadInfo:
    name: str
    namespace: str
    kind: str
    replicas: int
    ready_replicas: int
    status: str
    image: str | None


def _workload_status(replicas: int, ready: int) -> str:
    if replicas == 0:
        return WorkloadStatus.UNKNOWN.value
    if ready >= replicas:
        return WorkloadStatus.HEALTHY.value
    if ready > 0:
        return WorkloadStatus.DEGRADED.value
    return WorkloadStatus.FAILED.value


def _extract_image(item: dict) -> str | None:
    kind = item.get("kind", "")
    if kind == "Pod":
        containers = item.get("spec", {}).get("containers", [])
    else:
        containers = (
            item.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("containers", [])
        )
    if containers:
        return containers[0].get("image")
    return None


def _extract_replicas(item: dict) -> tuple[int, int]:
    kind = item.get("kind", "")
    status = item.get("status", {})
    spec = item.get("spec", {})

    if kind == "Pod":
        phase = status.get("phase", "Unknown")
        container_statuses = status.get("containerStatuses", [])
        total = len(container_statuses) or 1
        ready = sum(1 for c in container_statuses if c.get("ready"))
        if phase == "Succeeded":
            return 1, 1
        if phase == "Running":
            return total, ready
        return total, 0

    if kind == "Service":
        return 1, 1

    if kind == "Ingress":
        has_rules = bool(spec.get("rules"))
        has_lb = bool(status.get("loadBalancer", {}).get("ingress"))
        return 1, 1 if has_rules or has_lb else 0

    if kind == "DaemonSet":
        replicas = (
            status.get("desiredNumberScheduled")
            or status.get("currentNumberScheduled")
            or 0
        )
        ready = status.get("numberReady") or 0
        return int(replicas), int(ready)

    replicas = spec.get("replicas")
    if replicas is None:
        replicas = 1
    ready = status.get("readyReplicas") or status.get("availableReplicas") or 0
    return int(replicas), int(ready)


def _parse_kubectl_json(stdout: str) -> list[K8sWorkloadInfo]:
    data = json.loads(stdout)
    workloads: list[K8sWorkloadInfo] = []

    for item in data.get("items", []):
        kind = item.get("kind", "")
        mapped_kind = KIND_MAP.get(kind)
        if not mapped_kind:
            continue

        metadata = item.get("metadata", {})
        name = metadata.get("name")
        namespace = metadata.get("namespace", "default")
        if not name:
            continue

        replicas, ready = _extract_replicas(item)
        workloads.append(
            K8sWorkloadInfo(
                name=name,
                namespace=namespace,
                kind=mapped_kind,
                replicas=replicas,
                ready_replicas=ready,
                status=_workload_status(replicas, ready),
                image=_extract_image(item),
            )
        )

    return workloads


def fetch_workloads_from_node(node: Node, db: Session) -> list[K8sWorkloadInfo]:
    if not is_ssh_configured(db):
        raise ValueError("SSH credentials not configured. Add them in Settings first.")

    creds = get_decrypted_private_key(db)
    if not creds:
        raise ValueError("SSH credentials not configured.")

    global_user, private_key = creds
    username = resolve_node_ssh_user(node, global_user)

    result = exec_command(
        node.ip_address,
        node.ssh_port,
        username,
        private_key,
        KUBECTL_GET_CMD,
        timeout=90,
    )
    if not result.success and not result.stdout.strip():
        err = result.error or result.stderr or "Failed to list Kubernetes workloads"
        lower = err.lower()
        if "not found" in lower or "command not found" in lower or "127" in lower:
            raise ValueError("kubectl is not installed or Kubernetes is not available on this node")
        raise ValueError(err)

    stdout = result.stdout.strip()
    if not stdout:
        check = exec_command(
            node.ip_address,
            node.ssh_port,
            username,
            private_key,
            "command -v kubectl >/dev/null 2>&1 && echo ok || (command -v k3s >/dev/null 2>&1 && echo k3s || echo missing)",
        )
        hint = check.stdout.strip()
        if hint == "missing":
            raise ValueError("kubectl/k3s is not installed on this node")
        return []

    try:
        return _parse_kubectl_json(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse kubectl output: {exc}") from exc


def sync_node_workloads(db: Session, node: Node) -> tuple[list[Workload], int, int]:
    """Sync workloads for a node. Returns (workloads, synced, removed)."""
    live = fetch_workloads_from_node(node, db)
    live_keys = {(w.namespace, w.name, w.kind) for w in live}
    cluster_name = f"k3s-{node.name}"
    now = datetime.utcnow()

    existing = db.query(Workload).filter(Workload.node_id == node.id).all()
    existing_by_key = {(w.namespace, w.name, w.kind): w for w in existing}

    synced = 0
    for info in live:
        key = (info.namespace, info.name, info.kind)
        if key in existing_by_key:
            row = existing_by_key[key]
            old_status = row.status
            row.cluster_name = cluster_name
            row.replicas = info.replicas
            row.ready_replicas = info.ready_replicas
            row.status = info.status
            row.image = info.image
            row.updated_at = now
            if old_status != info.status:
                log_activity(
                    db,
                    event_type=ActivityEventType.WORKLOAD_STATUS_CHANGED.value,
                    message=f"Workload '{info.name}' in '{info.namespace}': {old_status} → {info.status}",
                    severity=ActivitySeverity.WARNING.value
                    if info.status in (WorkloadStatus.FAILED.value, WorkloadStatus.DEGRADED.value)
                    else ActivitySeverity.INFO.value,
                    related_entity_type="workload",
                    related_entity_id=row.id,
                )
        else:
            row = Workload(
                name=info.name,
                namespace=info.namespace,
                kind=info.kind,
                cluster_name=cluster_name,
                node_id=node.id,
                replicas=info.replicas,
                ready_replicas=info.ready_replicas,
                status=info.status,
                image=info.image,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
        synced += 1

    removed = 0
    for key, row in existing_by_key.items():
        if key not in live_keys:
            db.delete(row)
            removed += 1

    db.commit()

    workloads = (
        db.query(Workload)
        .filter(Workload.node_id == node.id)
        .order_by(Workload.namespace, Workload.name)
        .all()
    )

    log_activity(
        db,
        event_type=ActivityEventType.WORKLOAD_STATUS_CHANGED.value,
        message=f"Kubernetes sync on '{node.name}': {len(live)} workload(s) synced, {removed} removed",
        severity=ActivitySeverity.INFO.value,
        related_entity_type="node",
        related_entity_id=node.id,
    )

    return workloads, synced, removed
