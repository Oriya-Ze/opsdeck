from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.container import Container
from app.models.node import Node
from app.schemas.container import ContainerCreate, ContainerResponse, ContainerUpdate
from app.services.activity_service import log_activity
from app.models.enums import ActivityEventType, ActivitySeverity

router = APIRouter(prefix="/containers", tags=["Containers"])


@router.get("", response_model=list[ContainerResponse])
def list_containers(
    node_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Container)
    if node_id:
        query = query.filter(Container.node_id == node_id)
    return query.order_by(Container.name).all()


@router.post("", response_model=ContainerResponse, status_code=status.HTTP_201_CREATED)
def create_container(data: ContainerCreate, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == data.node_id).first()
    if not node:
        raise HTTPException(status_code=400, detail="Node not found")

    container = Container(**data.model_dump())
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


@router.get("/{container_id}", response_model=ContainerResponse)
def get_container(container_id: UUID, db: Session = Depends(get_db)):
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    return container


@router.put("/{container_id}", response_model=ContainerResponse)
def update_container(container_id: UUID, data: ContainerUpdate, db: Session = Depends(get_db)):
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")

    old_status = container.status
    if data.node_id:
        node = db.query(Node).filter(Node.id == data.node_id).first()
        if not node:
            raise HTTPException(status_code=400, detail="Node not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(container, field, value)

    db.commit()
    db.refresh(container)

    if data.status and old_status != container.status:
        log_activity(
            db,
            event_type=ActivityEventType.CONTAINER_STATUS_CHANGED.value,
            message=f"Container '{container.name}' status: {old_status} → {container.status}",
            severity=ActivitySeverity.WARNING.value if container.status in ("failed", "stopped") else ActivitySeverity.INFO.value,
            related_entity_type="container",
            related_entity_id=container.id,
        )
    return container


@router.delete("/{container_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_container(container_id: UUID, db: Session = Depends(get_db)):
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    db.delete(container)
    db.commit()
