from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.health_check import HealthCheck
from app.schemas.health_check import HealthCheckResponse

router = APIRouter(prefix="/health-checks", tags=["Health Checks"])


@router.get("", response_model=list[HealthCheckResponse])
def list_health_checks(
    target_type: str | None = Query(None),
    target_id: UUID | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(HealthCheck)
    if target_type:
        query = query.filter(HealthCheck.target_type == target_type)
    if target_id:
        query = query.filter(HealthCheck.target_id == target_id)
    return query.order_by(HealthCheck.checked_at.desc()).limit(limit).all()
