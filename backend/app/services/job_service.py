from uuid import UUID

from sqlalchemy.orm import Session

from app.models.container import Container
from app.models.enums import JobTargetType
from app.models.job import Job
from app.models.node import Node
from app.models.service import Service
from app.models.workload import Workload
from app.schemas.job import JobResponse


def resolve_target_name(db: Session, target_type: str, target_id: UUID) -> str | None:
    if target_type == JobTargetType.NODE.value:
        return db.query(Node.name).filter(Node.id == target_id).scalar()
    if target_type == JobTargetType.SERVICE.value:
        return db.query(Service.name).filter(Service.id == target_id).scalar()
    if target_type == JobTargetType.CONTAINER.value:
        return db.query(Container.name).filter(Container.id == target_id).scalar()
    if target_type == JobTargetType.WORKLOAD.value:
        return db.query(Workload.name).filter(Workload.id == target_id).scalar()
    return None


def job_to_response(db: Session, job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        job_id=job.job_id,
        action_name=job.action_name,
        target_type=job.target_type,
        target_id=job.target_id,
        target_name=resolve_target_name(db, job.target_type, job.target_id),
        status=job.status,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_by=job.created_by,
        output_log=job.output_log,
        error_log=job.error_log,
        created_at=job.created_at,
    )
