from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkloadBase(BaseModel):
    name: str = Field(..., max_length=150)
    namespace: str = "default"
    kind: str = "deployment"
    cluster_name: str = "k3s-local"
    node_id: UUID | None = None
    replicas: int = 1
    ready_replicas: int = 0
    status: str = "unknown"
    image: str | None = None


class WorkloadCreate(WorkloadBase):
    pass


class WorkloadUpdate(BaseModel):
    name: str | None = None
    namespace: str | None = None
    kind: str | None = None
    cluster_name: str | None = None
    node_id: UUID | None = None
    replicas: int | None = None
    ready_replicas: int | None = None
    status: str | None = None
    image: str | None = None


class WorkloadResponse(WorkloadBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
