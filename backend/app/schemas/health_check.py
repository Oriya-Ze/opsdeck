from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HealthCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_type: str
    target_id: UUID
    status: str
    response_time_ms: int | None = None
    message: str
    checked_at: datetime
