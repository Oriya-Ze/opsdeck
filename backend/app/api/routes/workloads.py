from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.node import Node
from app.models.workload import Workload
from app.schemas.workload import WorkloadCreate, WorkloadResponse, WorkloadUpdate
from app.services.activity_service import log_activity
from app.models.enums import ActivityEventType, ActivitySeverity

router = APIRouter(prefix="/workloads", tags=["Workloads"])


@router.get("", response_model=list[WorkloadResponse])
def list_workloads(
    node_id: UUID | None = Query(None, description="Filter workloads synced from this node"),
    db: Session = Depends(get_db),
):
    query = db.query(Workload)
    if node_id:
        query = query.filter(Workload.node_id == node_id)
    return query.order_by(Workload.namespace, Workload.name).all()


@router.post("", response_model=WorkloadResponse, status_code=status.HTTP_201_CREATED)
def create_workload(data: WorkloadCreate, db: Session = Depends(get_db)):
    if data.node_id:
        node = db.query(Node).filter(Node.id == data.node_id).first()
        if not node:
            raise HTTPException(status_code=400, detail="Node not found")

    workload = Workload(**data.model_dump())
    db.add(workload)
    db.commit()
    db.refresh(workload)
    return workload


@router.get("/{workload_id}", response_model=WorkloadResponse)
def get_workload(workload_id: UUID, db: Session = Depends(get_db)):
    workload = db.query(Workload).filter(Workload.id == workload_id).first()
    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")
    return workload


@router.put("/{workload_id}", response_model=WorkloadResponse)
def update_workload(workload_id: UUID, data: WorkloadUpdate, db: Session = Depends(get_db)):
    workload = db.query(Workload).filter(Workload.id == workload_id).first()
    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")

    old_status = workload.status
    if data.node_id:
        node = db.query(Node).filter(Node.id == data.node_id).first()
        if not node:
            raise HTTPException(status_code=400, detail="Node not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(workload, field, value)

    db.commit()
    db.refresh(workload)

    if data.status and old_status != workload.status:
        log_activity(
            db,
            event_type=ActivityEventType.WORKLOAD_STATUS_CHANGED.value,
            message=f"Workload '{workload.name}' status: {old_status} → {workload.status}",
            severity=ActivitySeverity.WARNING.value if workload.status in ("failed", "degraded") else ActivitySeverity.INFO.value,
            related_entity_type="workload",
            related_entity_id=workload.id,
        )
    return workload


@router.delete("/{workload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workload(workload_id: UUID, db: Session = Depends(get_db)):
    workload = db.query(Workload).filter(Workload.id == workload_id).first()
    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")
    db.delete(workload)
    db.commit()
