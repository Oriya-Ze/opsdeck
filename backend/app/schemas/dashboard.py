from datetime import datetime

from pydantic import BaseModel

from app.schemas.health_check import HealthCheckResponse
from app.schemas.job import JobResponse


class DashboardStats(BaseModel):
    total_nodes: int
    healthy_nodes: int
    warning_nodes: int
    offline_nodes: int
    running_services: int
    failed_services: int
    recent_jobs: list[JobResponse]
    last_health_check_at: datetime | None = None
