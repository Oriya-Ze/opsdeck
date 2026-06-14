from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import ActivityEventType, ActivitySeverity
from app.models.node import Node
from app.schemas.backup import (
    AutoBackupRunResponse,
    BackupRunResponse,
    BackupSettingsResponse,
    BackupSettingsUpdate,
    NodeBackupResponse,
    backup_settings_response_from_row,
)
from app.services.activity_service import log_activity
from app.services.backup_service import (
    create_node_backup,
    delete_node_backup,
    get_node_backup,
    list_node_backups,
    restore_node_backup,
    run_auto_backups,
)
from app.services.backup_settings_service import get_or_create_backup_settings, update_backup_settings

router = APIRouter(prefix="/settings/backup", tags=["Backup Settings"])


@router.get("", response_model=BackupSettingsResponse)
def get_backup_config(db: Session = Depends(get_db)):
    return backup_settings_response_from_row(get_or_create_backup_settings(db))


@router.put("", response_model=BackupSettingsResponse)
def save_backup_config(data: BackupSettingsUpdate, db: Session = Depends(get_db)):
    saved = update_backup_settings(db, data.model_dump(exclude_unset=True))
    log_activity(
        db,
        event_type=ActivityEventType.NODE_UPDATED.value,
        message="Node backup settings updated",
        severity=ActivitySeverity.INFO.value,
        related_entity_type="settings",
        related_entity_id=None,
    )
    return backup_settings_response_from_row(saved)


@router.post("/run-now", response_model=AutoBackupRunResponse)
def run_backup_now(db: Session = Depends(get_db)):
    result = run_auto_backups(db, force=True)
    return AutoBackupRunResponse(
        nodes_attempted=result.nodes_attempted,
        nodes_succeeded=result.nodes_succeeded,
        nodes_failed=result.nodes_failed,
        skipped=result.skipped,
        summary=result.summary,
        errors=result.errors,
    )


node_backup_router = APIRouter(prefix="/nodes", tags=["Node Backups"])


@node_backup_router.get("/{node_id}/backups", response_model=list[NodeBackupResponse])
def list_backups(node_id: UUID, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return list_node_backups(db, node_id)


@node_backup_router.post("/{node_id}/backups", response_model=BackupRunResponse)
def run_node_backup(node_id: UUID, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    result = create_node_backup(db, node)
    return BackupRunResponse(
        success=result.success,
        message=result.message,
        backup=NodeBackupResponse.model_validate(result.backup) if result.backup else None,
        error=result.error,
    )


@node_backup_router.post("/{node_id}/backups/{backup_id}/restore", response_model=BackupRunResponse)
def restore_backup(node_id: UUID, backup_id: UUID, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    backup = get_node_backup(db, node_id, backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    result = restore_node_backup(db, node, backup)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "Restore failed")
    return BackupRunResponse(success=True, message=result.message)


@node_backup_router.delete("/{node_id}/backups/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_backup(node_id: UUID, backup_id: UUID, db: Session = Depends(get_db)):
    backup = get_node_backup(db, node_id, backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    delete_node_backup(db, backup)
    log_activity(
        db,
        event_type=ActivityEventType.NODE_UPDATED.value,
        message=f"Deleted backup '{backup.filename}'",
        severity=ActivitySeverity.WARNING.value,
        related_entity_type="node",
        related_entity_id=node_id,
    )
