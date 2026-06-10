from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import ActivityEventType, JobTargetType
from app.models.node import Node
from app.schemas.health_check import HealthCheckResponse
from app.schemas.job import JobResponse
from app.schemas.container import ContainerSyncResponse
from app.schemas.workload import WorkloadSyncResponse
from app.schemas.node import NodeCreate, NodeResponse, NodeTestConnectionResponse, NodeUpdate
from app.services.docker_sync import sync_node_containers
from app.services.k8s_sync import sync_node_workloads
from app.services.activity_service import log_activity
from app.services.job_runner import create_and_run_job
from app.services.ssh_client import resolve_node_ssh_user, test_connection
from app.services.ssh_credentials import get_decrypted_private_key
from app.services.ssh_health import run_node_health_check

router = APIRouter(prefix="/nodes", tags=["Nodes"])

NODE_ACTIONS = {
    "health-check",
    "update-packages",
    "restart-docker",
    "install-node-exporter",
    "run-backup",
}


@router.get("", response_model=list[NodeResponse])
def list_nodes(db: Session = Depends(get_db)):
    return db.query(Node).order_by(Node.name).all()


@router.post("", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
def create_node(data: NodeCreate, db: Session = Depends(get_db)):
    existing = db.query(Node).filter(Node.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Node with this name already exists")

    node = Node(**data.model_dump())
    db.add(node)
    db.commit()
    db.refresh(node)

    log_activity(
        db,
        event_type=ActivityEventType.NODE_ADDED.value,
        message=f"Node '{node.name}' added to inventory",
        related_entity_type="node",
        related_entity_id=node.id,
    )
    return node


@router.get("/{node_id}", response_model=NodeResponse)
def get_node(node_id: UUID, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.put("/{node_id}", response_model=NodeResponse)
def update_node(node_id: UUID, data: NodeUpdate, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(node, field, value)

    db.commit()
    db.refresh(node)

    log_activity(
        db,
        event_type=ActivityEventType.NODE_UPDATED.value,
        message=f"Node '{node.name}' updated",
        related_entity_type="node",
        related_entity_id=node.id,
    )
    return node


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node(node_id: UUID, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    name = node.name
    db.delete(node)
    db.commit()

    log_activity(
        db,
        event_type=ActivityEventType.NODE_DELETED.value,
        message=f"Node '{name}' removed from inventory",
        related_entity_type="node",
        related_entity_id=node_id,
    )


@router.post("/{node_id}/test-connection", response_model=NodeTestConnectionResponse)
def test_node_connection(node_id: UUID, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    creds = get_decrypted_private_key(db)
    if not creds:
        raise HTTPException(
            status_code=400,
            detail="SSH credentials not configured. Go to Settings to add your SSH key.",
        )

    global_user, private_key = creds
    username = resolve_node_ssh_user(node, global_user)
    result = test_connection(node.ip_address, node.ssh_port, username, private_key)

    if result.success:
        return NodeTestConnectionResponse(
            success=True,
            message=f"Connected to {node.name} as {username}",
            response_time_ms=result.response_time_ms,
            output=result.stdout,
        )
    return NodeTestConnectionResponse(
        success=False,
        message=result.error or result.stderr or "Connection failed",
        response_time_ms=result.response_time_ms,
    )


@router.post("/{node_id}/sync-containers", response_model=ContainerSyncResponse)
def sync_containers(node_id: UUID, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    try:
        containers, synced, removed = sync_node_containers(db, node)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return ContainerSyncResponse(
        node_id=node.id,
        node_name=node.name,
        synced=synced,
        removed=removed,
        containers=containers,
    )


@router.post("/{node_id}/sync-workloads", response_model=WorkloadSyncResponse)
def sync_workloads(node_id: UUID, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    try:
        workloads, synced, removed = sync_node_workloads(db, node)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return WorkloadSyncResponse(
        node_id=node.id,
        node_name=node.name,
        synced=synced,
        removed=removed,
        workloads=workloads,
    )


@router.post("/{node_id}/health-check", response_model=HealthCheckResponse)
def node_health_check(node_id: UUID, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return run_node_health_check(db, node)


@router.post("/{node_id}/actions/{action_name}", response_model=JobResponse)
def node_action(node_id: UUID, action_name: str, db: Session = Depends(get_db)):
    if action_name not in NODE_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action_name}")

    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if action_name == "health-check":
        run_node_health_check(db, node)

    return create_and_run_job(
        db,
        action_name=action_name,
        target_type=JobTargetType.NODE.value,
        target_id=node.id,
        node=node,
    )
