from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import JobStatus, NodeStatus, ServiceStatus
from app.models.health_check import HealthCheck
from app.models.job import Job
from app.models.node import Node
from app.models.service import Service
from app.schemas.dashboard import DashboardStats


def get_dashboard_stats(db: Session) -> DashboardStats:
    total_nodes = db.query(func.count(Node.id)).scalar() or 0
    healthy_nodes = db.query(func.count(Node.id)).filter(Node.status == NodeStatus.HEALTHY.value).scalar() or 0
    warning_nodes = db.query(func.count(Node.id)).filter(Node.status == NodeStatus.WARNING.value).scalar() or 0
    offline_nodes = db.query(func.count(Node.id)).filter(Node.status == NodeStatus.OFFLINE.value).scalar() or 0

    running_services = db.query(func.count(Service.id)).filter(Service.status == ServiceStatus.UP.value).scalar() or 0
    failed_services = db.query(func.count(Service.id)).filter(Service.status == ServiceStatus.DOWN.value).scalar() or 0

    recent_jobs = (
        db.query(Job)
        .order_by(Job.created_at.desc())
        .limit(5)
        .all()
    )

    last_check = db.query(func.max(HealthCheck.checked_at)).scalar()

    return DashboardStats(
        total_nodes=total_nodes,
        healthy_nodes=healthy_nodes,
        warning_nodes=warning_nodes,
        offline_nodes=offline_nodes,
        running_services=running_services,
        failed_services=failed_services,
        recent_jobs=recent_jobs,
        last_health_check_at=last_check,
    )
