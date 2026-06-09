from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContainerBase(BaseModel):
    name: str = Field(..., max_length=150)
    image: str
    node_id: UUID
    status: str = "unknown"
    ports: str | None = None
    restart_count: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0


class ContainerCreate(ContainerBase):
    pass


class ContainerUpdate(BaseModel):
    name: str | None = None
    image: str | None = None
    node_id: UUID | None = None
    status: str | None = None
    ports: str | None = None
    restart_count: int | None = None
    cpu_usage: float | None = None
    memory_usage: float | None = None


class ContainerResponse(ContainerBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class ContainerSyncResponse(BaseModel):
    node_id: UUID
    node_name: str
    synced: int
    removed: int
    containers: list[ContainerResponse]
