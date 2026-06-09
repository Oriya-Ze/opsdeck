import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.enums import ActivityEventType, ActivitySeverity


def log_activity(
    db: Session,
    event_type: str,
    message: str,
    severity: str = ActivitySeverity.INFO.value,
    related_entity_type: str | None = None,
    related_entity_id: uuid.UUID | None = None,
) -> ActivityLog:
    entry = ActivityLog(
        timestamp=datetime.utcnow(),
        event_type=event_type,
        message=message,
        severity=severity,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
