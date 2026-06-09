from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ServiceBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = None
    url: str | None = None
    node_id: UUID
    port: int | None = None
    protocol: str = "http"
    status: str = "unknown"
    category: str = "other"
    notes: str | None = None


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    url: str | None = None
    node_id: UUID | None = None
    port: int | None = None
    protocol: str | None = None
    status: str | None = None
    category: str | None = None
    notes: str | None = None


class ServiceResponse(ServiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    last_checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
