from datetime import datetime

from sqlalchemy.orm import Session

from app.models.sync_settings import SyncSettings


def get_sync_settings(db: Session) -> SyncSettings | None:
    return db.query(SyncSettings).filter(SyncSettings.id == 1).first()


def get_or_create_sync_settings(db: Session) -> SyncSettings:
    row = get_sync_settings(db)
    if row:
        return row
    row = SyncSettings(id=1)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_sync_settings(db: Session, data: dict) -> SyncSettings:
    row = get_or_create_sync_settings(db)
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def record_auto_sync_result(db: Session, summary: str) -> SyncSettings:
    row = get_or_create_sync_settings(db)
    row.last_auto_sync_at = datetime.utcnow()
    row.last_auto_sync_summary = summary
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row
