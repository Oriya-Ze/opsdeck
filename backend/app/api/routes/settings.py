from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.ssh_settings import (
    SshGenerateResponse,
    SshSettingsResponse,
    SshSettingsSave,
    SshTestRequest,
    SshTestResponse,
)
from app.services.activity_service import log_activity
from app.services.encryption import decrypt_value
from app.services.ssh_client import test_connection
from app.services.ssh_credentials import (
    delete_ssh_settings,
    get_ssh_settings,
    save_ssh_settings,
)
from app.services.ssh_keygen import generate_ssh_keypair
from app.models.enums import ActivityEventType, ActivitySeverity

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/ssh", response_model=SshSettingsResponse)
def get_ssh_config(db: Session = Depends(get_db)):
    settings = get_ssh_settings(db)
    if not settings:
        return SshSettingsResponse(configured=False)
    return SshSettingsResponse(
        configured=True,
        ssh_user=settings.ssh_user,
        key_fingerprint=settings.key_fingerprint,
        public_key=settings.public_key,
        updated_at=settings.updated_at,
    )


@router.put("/ssh", response_model=SshSettingsResponse)
def save_ssh_config(data: SshSettingsSave, db: Session = Depends(get_db)):
    try:
        saved = save_ssh_settings(
            db,
            ssh_user=data.ssh_user,
            private_key=data.private_key,
            public_key=data.public_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    log_activity(
        db,
        event_type=ActivityEventType.NODE_UPDATED.value,
        message=f"SSH credentials updated for user '{saved.ssh_user}'",
        severity=ActivitySeverity.INFO.value,
        related_entity_type="settings",
        related_entity_id=None,
    )

    return SshSettingsResponse(
        configured=True,
        ssh_user=saved.ssh_user,
        key_fingerprint=saved.key_fingerprint,
        public_key=saved.public_key,
        updated_at=saved.updated_at,
    )


@router.delete("/ssh", status_code=204)
def remove_ssh_config(db: Session = Depends(get_db)):
    if not delete_ssh_settings(db):
        raise HTTPException(status_code=404, detail="SSH credentials not configured")
    log_activity(
        db,
        event_type=ActivityEventType.NODE_UPDATED.value,
        message="SSH credentials removed",
        severity=ActivitySeverity.WARNING.value,
        related_entity_type="settings",
        related_entity_id=None,
    )


@router.post("/ssh/test", response_model=SshTestResponse)
def test_ssh_connection(data: SshTestRequest, db: Session = Depends(get_db)):
    private_key = data.private_key
    ssh_user = data.ssh_user

    if not private_key or not ssh_user:
        stored = get_ssh_settings(db)
        if not stored:
            raise HTTPException(
                status_code=400,
                detail="Provide private_key and ssh_user, or save credentials first",
            )
        ssh_user = ssh_user or stored.ssh_user
        private_key = decrypt_value(stored.encrypted_private_key)

    result = test_connection(data.host, data.port, ssh_user, private_key)

    if result.success:
        return SshTestResponse(
            success=True,
            message="SSH connection successful",
            response_time_ms=result.response_time_ms,
            output=result.stdout,
        )
    return SshTestResponse(
        success=False,
        message=result.error or result.stderr or "Connection failed",
        response_time_ms=result.response_time_ms,
    )


@router.post("/ssh/generate", response_model=SshGenerateResponse)
def generate_ssh_key():
    keys = generate_ssh_keypair()
    return SshGenerateResponse(**keys)
