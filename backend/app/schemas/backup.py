from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.services.backup_storage import storage_type


class BackupSettingsResponse(BaseModel):
    auto_backup_enabled: bool
    backup_interval_seconds: int
    last_auto_backup_at: datetime | None = None
    last_auto_backup_summary: str | None = None
    updated_at: datetime | None = None
    storage_type: str = Field(default_factory=storage_type)
    backup_local_dir: str | None = None
    s3_bucket: str | None = None
    s3_region: str | None = None


class BackupSettingsUpdate(BaseModel):
    auto_backup_enabled: bool | None = None
    backup_interval_seconds: int | None = Field(None, ge=3600, le=604800)


class NodeBackupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    node_id: UUID
    filename: str
    storage_type: str
    storage_path: str
    size_bytes: int
    status: str
    error_message: str | None = None
    created_at: datetime


class BackupRunResponse(BaseModel):
    success: bool
    message: str
    backup: NodeBackupResponse | None = None
    error: str | None = None


class AutoBackupRunResponse(BaseModel):
    nodes_attempted: int
    nodes_succeeded: int
    nodes_failed: int
    skipped: bool = False
    summary: str
    errors: list[str] | None = None


def backup_settings_response_from_row(row) -> BackupSettingsResponse:
    return BackupSettingsResponse(
        auto_backup_enabled=row.auto_backup_enabled,
        backup_interval_seconds=row.backup_interval_seconds,
        last_auto_backup_at=row.last_auto_backup_at,
        last_auto_backup_summary=row.last_auto_backup_summary,
        updated_at=row.updated_at,
        storage_type=storage_type(),
        backup_local_dir=settings.BACKUP_LOCAL_DIR if settings.STORAGE_TYPE.value == "local" else None,
        s3_bucket=settings.S3_BUCKET,
        s3_region=settings.S3_REGION,
    )
