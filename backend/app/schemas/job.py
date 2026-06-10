from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: str
    action_name: str
    target_type: str
    target_id: UUID
    target_name: str | None = None
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_by: str
    output_log: str | None = None
    error_log: str | None = None
    created_at: datetime
