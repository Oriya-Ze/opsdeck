from datetime import datetime

from pydantic import BaseModel, Field


class SyncSettingsResponse(BaseModel):
    containers_auto_sync_enabled: bool
    containers_sync_interval_seconds: int
    last_auto_sync_at: datetime | None = None
    last_auto_sync_summary: str | None = None
    updated_at: datetime | None = None


class SyncSettingsUpdate(BaseModel):
    containers_auto_sync_enabled: bool | None = None
    containers_sync_interval_seconds: int | None = Field(None, ge=60, le=3600)


class AutoSyncRunResponse(BaseModel):
    nodes_attempted: int
    nodes_succeeded: int
    nodes_failed: int
    total_containers: int
    summary: str
    errors: list[str]
