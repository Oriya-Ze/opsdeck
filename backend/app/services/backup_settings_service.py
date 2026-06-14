from datetime import datetime

from sqlalchemy.orm import Session

from app.models.backup import BackupSettings


def get_backup_settings(db: Session) -> BackupSettings | None:
    return db.query(BackupSettings).filter(BackupSettings.id == 1).first()


def get_or_create_backup_settings(db: Session) -> BackupSettings:
    row = get_backup_settings(db)
    if row:
        return row
    row = BackupSettings(id=1)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_backup_settings(db: Session, data: dict) -> BackupSettings:
    row = get_or_create_backup_settings(db)
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def record_auto_backup_result(db: Session, summary: str) -> BackupSettings:
    row = get_or_create_backup_settings(db)
    row.last_auto_backup_at = datetime.utcnow()
    row.last_auto_backup_summary = summary
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row
