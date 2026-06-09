"""Seed database with realistic demo data."""
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.container import Container
from app.models.enums import (
    ActivityEventType,
    ActivitySeverity,
    ContainerStatus,
    HealthCheckStatus,
    HealthCheckTargetType,
    JobStatus,
    JobTargetType,
    NodeEnvironment,
    NodeRole,
    NodeStatus,
    ServiceCategory,
    ServiceProtocol,
    ServiceStatus,
    WorkloadKind,
    WorkloadStatus,
)
from app.models.health_check import HealthCheck
from app.models.job import Job
from app.models.node import Node
from app.models.service import Service
from app.models.workload import Workload


def seed_database(db: Session) -> None:
    if db.query(Node).count() > 0:
        return

    now = datetime.utcnow()

    # Nodes
    pi_id = uuid.uuid4()
    vm_id = uuid.uuid4()
    k3s_id = uuid.uuid4()

    nodes = [
        Node(
            id=pi_id,
            name="raspberry-pi-01",
            hostname="raspberry-pi-01.local",
            ip_address="192.168.1.10",
            ssh_port=22,
            os_name="Raspberry Pi OS 12",
            environment=NodeEnvironment.LOCAL.value,
            role=NodeRole.RASPBERRY_PI.value,
            status=NodeStatus.HEALTHY.value,
            cpu_usage=18.5,
            ram_usage=42.3,
            disk_usage=61.2,
            uptime="45d 12h",
            last_checked_at=now - timedelta(minutes=5),
            notes="Home automation and monitoring node",
        ),
        Node(
            id=vm_id,
            name="ubuntu-vm-01",
            hostname="ubuntu-vm-01.lab",
            ip_address="192.168.1.20",
            ssh_port=22,
            os_name="Ubuntu 24.04 LTS",
            environment=NodeEnvironment.LAB.value,
            role=NodeRole.VM.value,
            status=NodeStatus.HEALTHY.value,
            cpu_usage=32.1,
            ram_usage=58.7,
            disk_usage=44.0,
            uptime="12d 6h",
            last_checked_at=now - timedelta(minutes=3),
            notes="Docker host for core services",
        ),
        Node(
            id=k3s_id,
            name="k3s-master-01",
            hostname="k3s-master-01.lab",
            ip_address="192.168.1.30",
            ssh_port=22,
            os_name="Ubuntu 22.04 LTS",
            environment=NodeEnvironment.LAB.value,
            role=NodeRole.MASTER.value,
            status=NodeStatus.WARNING.value,
            cpu_usage=67.4,
            ram_usage=72.1,
            disk_usage=38.5,
            uptime="30d 2h",
            last_checked_at=now - timedelta(minutes=10),
            notes="K3s control plane and worker",
        ),
    ]
    db.add_all(nodes)

    # Services
    services_data = [
        ("Grafana", "Metrics visualization dashboard", "http://grafana.lab", vm_id, 3000, ServiceProtocol.HTTP.value, ServiceStatus.UP.value, ServiceCategory.MONITORING.value),
        ("Prometheus", "Time-series metrics collection", "http://prometheus.lab", vm_id, 9090, ServiceProtocol.HTTP.value, ServiceStatus.UP.value, ServiceCategory.MONITORING.value),
        ("ArgoCD", "GitOps continuous delivery", "https://argocd.lab", k3s_id, 443, ServiceProtocol.HTTPS.value, ServiceStatus.UP.value, ServiceCategory.GITOPS.value),
        ("Portainer", "Docker container management UI", "https://portainer.lab", vm_id, 9443, ServiceProtocol.HTTPS.value, ServiceStatus.UP.value, ServiceCategory.APP.value),
        ("Nginx Proxy Manager", "Reverse proxy management", "http://npm.lab", vm_id, 81, ServiceProtocol.HTTP.value, ServiceStatus.UP.value, ServiceCategory.PROXY.value),
        ("MinIO", "S3-compatible object storage", "http://minio.lab", vm_id, 9000, ServiceProtocol.HTTP.value, ServiceStatus.WARNING.value, ServiceCategory.STORAGE.value),
        ("PostgreSQL", "Primary relational database", "tcp://postgres.lab", vm_id, 5432, ServiceProtocol.TCP.value, ServiceStatus.UP.value, ServiceCategory.DATABASE.value),
        ("Redis", "In-memory cache and queue", "tcp://redis.lab", pi_id, 6379, ServiceProtocol.TCP.value, ServiceStatus.UP.value, ServiceCategory.DATABASE.value),
    ]

    service_ids = []
    for name, desc, url, node_id, port, protocol, status, category in services_data:
        sid = uuid.uuid4()
        service_ids.append(sid)
        db.add(Service(
            id=sid,
            name=name,
            description=desc,
            url=url,
            node_id=node_id,
            port=port,
            protocol=protocol,
            status=status,
            category=category,
            last_checked_at=now - timedelta(minutes=15),
        ))

    # Containers
    containers_data = [
        ("grafana", "grafana/grafana:11.0.0", vm_id, ContainerStatus.RUNNING.value, "3000:3000", 0, 2.1, 256.0),
        ("prometheus", "prom/prometheus:v2.53.0", vm_id, ContainerStatus.RUNNING.value, "9090:9090", 0, 4.5, 512.0),
        ("portainer", "portainer/portainer-ce:2.20.0", vm_id, ContainerStatus.RUNNING.value, "9443:9443", 1, 1.2, 128.0),
        ("nginx-proxy-manager", "jc21/nginx-proxy-manager:latest", vm_id, ContainerStatus.RUNNING.value, "80:80,443:443,81:81", 0, 0.8, 96.0),
        ("minio", "minio/minio:latest", vm_id, ContainerStatus.RUNNING.value, "9000:9000,9001:9001", 2, 3.2, 384.0),
        ("postgres", "postgres:16-alpine", vm_id, ContainerStatus.RUNNING.value, "5432:5432", 0, 5.1, 256.0),
        ("redis", "redis:7-alpine", pi_id, ContainerStatus.RUNNING.value, "6379:6379", 0, 0.5, 32.0),
        ("node-exporter", "prom/node-exporter:v1.8.0", pi_id, ContainerStatus.RUNNING.value, "9100:9100", 0, 0.3, 16.0),
        ("cadvisor", "gcr.io/cadvisor/cadvisor:v0.49.0", vm_id, ContainerStatus.STOPPED.value, "8080:8080", 3, 0.0, 0.0),
        ("watchtower", "containrrr/watchtower:latest", vm_id, ContainerStatus.RUNNING.value, None, 0, 0.1, 8.0),
    ]

    container_ids = []
    for name, image, node_id, status, ports, restarts, cpu, mem in containers_data:
        cid = uuid.uuid4()
        container_ids.append(cid)
        db.add(Container(
            id=cid,
            name=name,
            image=image,
            node_id=node_id,
            status=status,
            ports=ports,
            restart_count=restarts,
            cpu_usage=cpu,
            memory_usage=mem,
            created_at=now - timedelta(days=30),
            updated_at=now - timedelta(hours=2),
        ))

    # Workloads
    workloads_data = [
        ("argocd-server", "argocd", WorkloadKind.DEPLOYMENT.value, k3s_id, k3s_id, 1, 1, WorkloadStatus.HEALTHY.value, "quay.io/argoproj/argocd:v2.12.0"),
        ("nginx-ingress", "ingress-nginx", WorkloadKind.DEPLOYMENT.value, k3s_id, k3s_id, 1, 1, WorkloadStatus.HEALTHY.value, "registry.k8s.io/ingress-nginx/controller:v1.11.0"),
        ("opsdeck-api", "opsdeck", WorkloadKind.DEPLOYMENT.value, k3s_id, k3s_id, 2, 2, WorkloadStatus.HEALTHY.value, "opsdeck/api:latest"),
        ("redis-stateful", "cache", WorkloadKind.STATEFULSET.value, k3s_id, k3s_id, 1, 1, WorkloadStatus.HEALTHY.value, "redis:7-alpine"),
        ("node-exporter-ds", "monitoring", WorkloadKind.DAEMONSET.value, k3s_id, None, 3, 3, WorkloadStatus.HEALTHY.value, "prom/node-exporter:v1.8.0"),
        ("broken-app", "default", WorkloadKind.DEPLOYMENT.value, k3s_id, k3s_id, 2, 0, WorkloadStatus.FAILED.value, "nginx:broken-tag"),
    ]

    workload_ids = []
    for name, ns, kind, node_id, nid, replicas, ready, status, image in workloads_data:
        wid = uuid.uuid4()
        workload_ids.append(wid)
        db.add(Workload(
            id=wid,
            name=name,
            namespace=ns,
            kind=kind,
            cluster_name="k3s-local",
            node_id=nid,
            replicas=replicas,
            ready_replicas=ready,
            status=status,
            image=image,
            updated_at=now - timedelta(hours=1),
        ))

    # Jobs
    jobs_data = [
        ("job-a1b2c3d4", "health-check", JobTargetType.NODE.value, pi_id, JobStatus.SUCCESS.value),
        ("job-e5f6g7h8", "update-packages", JobTargetType.NODE.value, vm_id, JobStatus.SUCCESS.value),
        ("job-i9j0k1l2", "restart-docker", JobTargetType.NODE.value, vm_id, JobStatus.SUCCESS.value),
        ("job-m3n4o5p6", "install-node-exporter", JobTargetType.NODE.value, pi_id, JobStatus.SUCCESS.value),
        ("job-q7r8s9t0", "run-backup", JobTargetType.NODE.value, k3s_id, JobStatus.FAILED.value),
        ("job-u1v2w3x4", "health-check", JobTargetType.NODE.value, k3s_id, JobStatus.SUCCESS.value),
        ("job-y5z6a7b8", "update-packages", JobTargetType.NODE.value, k3s_id, JobStatus.RUNNING.value),
        ("job-c9d0e1f2", "restart-docker", JobTargetType.NODE.value, pi_id, JobStatus.PENDING.value),
    ]

    job_logs = {
        JobStatus.SUCCESS.value: "Checking SSH connectivity...\nGathering system information...\nRunning selected automation task...\nTask completed successfully.",
        JobStatus.FAILED.value: "Checking SSH connectivity...\nGathering system information...\nRunning selected automation task...",
        JobStatus.RUNNING.value: "Checking SSH connectivity...\nGathering system information...",
        JobStatus.PENDING.value: None,
    }

    for job_id_str, action, target_type, target_id, status in jobs_data:
        started = now - timedelta(hours=2) if status != JobStatus.PENDING.value else None
        finished = now - timedelta(hours=1, minutes=55) if status in (JobStatus.SUCCESS.value, JobStatus.FAILED.value) else None
        db.add(Job(
            id=uuid.uuid4(),
            job_id=job_id_str,
            action_name=action,
            target_type=target_type,
            target_id=target_id,
            status=status,
            started_at=started,
            finished_at=finished,
            created_by="admin",
            output_log=job_logs.get(status),
            error_log="Error: Task failed during execution." if status == JobStatus.FAILED.value else None,
            created_at=now - timedelta(hours=3),
        ))

    # Health checks
    hc_targets = [
        (HealthCheckTargetType.NODE.value, pi_id, HealthCheckStatus.SUCCESS.value, 45, "SSH connectivity verified. All metrics within normal range."),
        (HealthCheckTargetType.NODE.value, vm_id, HealthCheckStatus.SUCCESS.value, 32, "Node responsive. CPU, RAM, and disk usage nominal."),
        (HealthCheckTargetType.NODE.value, k3s_id, HealthCheckStatus.WARNING.value, 120, "Node reachable but disk usage above 80%."),
        (HealthCheckTargetType.SERVICE.value, service_ids[0], HealthCheckStatus.SUCCESS.value, 28, "HTTP 200 OK. Service responding normally."),
        (HealthCheckTargetType.SERVICE.value, service_ids[1], HealthCheckStatus.SUCCESS.value, 35, "Endpoint reachable. Response time acceptable."),
        (HealthCheckTargetType.SERVICE.value, service_ids[2], HealthCheckStatus.SUCCESS.value, 55, "Health endpoint returned healthy status."),
        (HealthCheckTargetType.SERVICE.value, service_ids[3], HealthCheckStatus.SUCCESS.value, 42, "HTTP 200 OK. Service responding normally."),
        (HealthCheckTargetType.SERVICE.value, service_ids[4], HealthCheckStatus.SUCCESS.value, 38, "Endpoint reachable. Response time acceptable."),
        (HealthCheckTargetType.SERVICE.value, service_ids[5], HealthCheckStatus.WARNING.value, 2100, "Slow response detected (>2s)."),
        (HealthCheckTargetType.SERVICE.value, service_ids[6], HealthCheckStatus.SUCCESS.value, 15, "TCP port open and accepting connections."),
        (HealthCheckTargetType.SERVICE.value, service_ids[7], HealthCheckStatus.SUCCESS.value, 12, "TCP port open and accepting connections."),
        (HealthCheckTargetType.NODE.value, pi_id, HealthCheckStatus.SUCCESS.value, 48, "Health check passed. Uptime stable."),
        (HealthCheckTargetType.NODE.value, vm_id, HealthCheckStatus.SUCCESS.value, 30, "SSH OK. All probes passed."),
        (HealthCheckTargetType.SERVICE.value, service_ids[0], HealthCheckStatus.SUCCESS.value, 25, "Grafana dashboard accessible."),
        (HealthCheckTargetType.SERVICE.value, service_ids[1], HealthCheckStatus.WARNING.value, 890, "Prometheus scrape targets partially down."),
    ]

    for i, (tt, tid, status, rt, msg) in enumerate(hc_targets):
        db.add(HealthCheck(
            id=uuid.uuid4(),
            target_type=tt,
            target_id=tid,
            status=status,
            response_time_ms=rt,
            message=msg,
            checked_at=now - timedelta(hours=i + 1),
        ))

    # Activity logs
    activities = [
        (ActivityEventType.NODE_ADDED.value, "Node 'raspberry-pi-01' added to inventory", ActivitySeverity.INFO.value, "node", pi_id),
        (ActivityEventType.NODE_ADDED.value, "Node 'ubuntu-vm-01' added to inventory", ActivitySeverity.INFO.value, "node", vm_id),
        (ActivityEventType.NODE_ADDED.value, "Node 'k3s-master-01' added to inventory", ActivitySeverity.INFO.value, "node", k3s_id),
        (ActivityEventType.HEALTH_CHECK_EXECUTED.value, "Health check on node 'raspberry-pi-01': success", ActivitySeverity.INFO.value, "node", pi_id),
        (ActivityEventType.HEALTH_CHECK_EXECUTED.value, "Health check on node 'ubuntu-vm-01': success", ActivitySeverity.INFO.value, "node", vm_id),
        (ActivityEventType.HEALTH_CHECK_EXECUTED.value, "Health check on node 'k3s-master-01': warning", ActivitySeverity.WARNING.value, "node", k3s_id),
        (ActivityEventType.JOB_STARTED.value, "Job job-a1b2c3d4 started: health-check", ActivitySeverity.INFO.value, "node", pi_id),
        (ActivityEventType.JOB_COMPLETED.value, "Job job-a1b2c3d4 completed successfully: health-check", ActivitySeverity.INFO.value, "node", pi_id),
        (ActivityEventType.JOB_STARTED.value, "Job job-e5f6g7h8 started: update-packages", ActivitySeverity.INFO.value, "node", vm_id),
        (ActivityEventType.JOB_COMPLETED.value, "Job job-e5f6g7h8 completed successfully: update-packages", ActivitySeverity.INFO.value, "node", vm_id),
        (ActivityEventType.JOB_STARTED.value, "Job job-q7r8s9t0 started: run-backup", ActivitySeverity.INFO.value, "node", k3s_id),
        (ActivityEventType.JOB_COMPLETED.value, "Job job-q7r8s9t0 failed: run-backup", ActivitySeverity.ERROR.value, "node", k3s_id),
        (ActivityEventType.SERVICE_STATUS_CHANGED.value, "Service 'MinIO' status changed: up → warning", ActivitySeverity.WARNING.value, "service", service_ids[5]),
        (ActivityEventType.CONTAINER_STATUS_CHANGED.value, "Container 'cadvisor' status: running → stopped", ActivitySeverity.WARNING.value, "container", container_ids[8]),
        (ActivityEventType.WORKLOAD_STATUS_CHANGED.value, "Workload 'broken-app' status: degraded → failed", ActivitySeverity.ERROR.value, "workload", workload_ids[5]),
        (ActivityEventType.HEALTH_CHECK_EXECUTED.value, "Health check on service 'Grafana': success", ActivitySeverity.INFO.value, "service", service_ids[0]),
        (ActivityEventType.HEALTH_CHECK_EXECUTED.value, "Health check on service 'Prometheus': warning", ActivitySeverity.WARNING.value, "service", service_ids[1]),
        (ActivityEventType.NODE_UPDATED.value, "Node 'k3s-master-01' updated", ActivitySeverity.INFO.value, "node", k3s_id),
        (ActivityEventType.JOB_STARTED.value, "Job job-y5z6a7b8 started: update-packages", ActivitySeverity.INFO.value, "node", k3s_id),
        (ActivityEventType.SERVICE_STATUS_CHANGED.value, "Service 'ArgoCD' status changed: unknown → up", ActivitySeverity.INFO.value, "service", service_ids[2]),
    ]

    for i, (event, msg, sev, etype, eid) in enumerate(activities):
        db.add(ActivityLog(
            id=uuid.uuid4(),
            timestamp=now - timedelta(hours=i),
            event_type=event,
            message=msg,
            severity=sev,
            related_entity_type=etype,
            related_entity_id=eid,
        ))

    db.commit()
