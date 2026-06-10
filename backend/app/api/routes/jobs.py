from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import JobTargetType
from app.models.job import Job
from app.models.node import Node
from app.schemas.custom_playbook import PlaybookActionResponse
from app.schemas.job import JobResponse
from app.services.ansible_runner import get_action_catalog, is_ansible_available
from app.services.job_runner import rerun_job
from app.services.job_service import job_to_response

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/actions", response_model=list[PlaybookActionResponse])
def list_job_actions(db: Session = Depends(get_db)):
    runner = "ansible" if is_ansible_available() else "shell"
    return [
        PlaybookActionResponse(
            name=action.name,
            label=action.label,
            description=action.description,
            requires_sudo=action.requires_sudo,
            timeout_seconds=action.timeout_seconds,
            source=action.source,
            runner=runner,
            is_editable=action.source == "custom",
            custom_id=action.custom_id,
        )
        for action in get_action_catalog(db)
    ]


@router.get("", response_model=list[JobResponse])
def list_jobs(
    node_id: UUID | None = Query(None, description="Filter jobs targeting this node"),
    db: Session = Depends(get_db),
):
    query = db.query(Job)
    if node_id:
        query = query.filter(
            Job.target_type == JobTargetType.NODE.value,
            Job.target_id == node_id,
        )
    jobs = query.order_by(Job.created_at.desc()).all()
    return [job_to_response(db, job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_response(db, job)


@router.post("/{job_id}/rerun", response_model=JobResponse)
def rerun(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    node = None
    if job.target_type == JobTargetType.NODE.value:
        node = db.query(Node).filter(Node.id == job.target_id).first()

    new_job = rerun_job(db, job, node=node)
    return job_to_response(db, new_job)
