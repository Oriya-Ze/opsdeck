from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NodeBase(BaseModel):
    name: str = Field(..., max_length=100)
    hostname: str
    ip_address: str
    ssh_port: int = 22
    ssh_user: str | None = None
    os_name: str
    environment: str = "local"
    role: str = "server"
    status: str = "unknown"
    cpu_usage: float = 0.0
    ram_usage: float = 0.0
    disk_usage: float = 0.0
    uptime: str = "unknown"
    auto_sync_containers: bool = True
    notes: str | None = None


class NodeCreate(NodeBase):
    pass


class NodeUpdate(BaseModel):
    name: str | None = None
    hostname: str | None = None
    ip_address: str | None = None
    ssh_port: int | None = None
    ssh_user: str | None = None
    os_name: str | None = None
    environment: str | None = None
    role: str | None = None
    status: str | None = None
    cpu_usage: float | None = None
    ram_usage: float | None = None
    disk_usage: float | None = None
    uptime: str | None = None
    auto_sync_containers: bool | None = None
    notes: str | None = None


class NodeResponse(NodeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    last_checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class NodeTestConnectionResponse(BaseModel):
    success: bool
    message: str
    response_time_ms: int | None = None
    output: str | None = None
