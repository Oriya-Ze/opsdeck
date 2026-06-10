from uuid import UUID

from sqlalchemy.orm import Session

from app.models.custom_playbook import CustomPlaybook
from app.models.enums import ActivityEventType, ActivitySeverity
from app.services.activity_service import log_activity
from app.services.ansible_runner import BUILTIN_ACTION_NAMES

RESERVED_NAMES = BUILTIN_ACTION_NAMES


def list_custom_playbooks(db: Session) -> list[CustomPlaybook]:
    return db.query(CustomPlaybook).order_by(CustomPlaybook.name).all()


def get_custom_playbook(db: Session, playbook_id: UUID) -> CustomPlaybook | None:
    return db.query(CustomPlaybook).filter(CustomPlaybook.id == playbook_id).first()


def get_custom_playbook_by_name(db: Session, name: str) -> CustomPlaybook | None:
    return db.query(CustomPlaybook).filter(CustomPlaybook.name == name).first()


def create_custom_playbook(db: Session, data: dict) -> CustomPlaybook:
    if data["name"] in RESERVED_NAMES:
        raise ValueError(f"Name '{data['name']}' is reserved for a built-in action")

    existing = get_custom_playbook_by_name(db, data["name"])
    if existing:
        raise ValueError(f"Playbook '{data['name']}' already exists")

    row = CustomPlaybook(**data)
    db.add(row)
    db.commit()
    db.refresh(row)

    log_activity(
        db,
        event_type=ActivityEventType.JOB_STARTED.value,
        message=f"Custom playbook '{row.name}' created",
        severity=ActivitySeverity.INFO.value,
        related_entity_type="playbook",
        related_entity_id=row.id,
    )
    return row


def update_custom_playbook(db: Session, row: CustomPlaybook, data: dict) -> CustomPlaybook:
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_custom_playbook(db: Session, row: CustomPlaybook) -> None:
    name = row.name
    db.delete(row)
    db.commit()
    log_activity(
        db,
        event_type=ActivityEventType.JOB_COMPLETED.value,
        message=f"Custom playbook '{name}' deleted",
        severity=ActivitySeverity.WARNING.value,
        related_entity_type="playbook",
        related_entity_id=None,
    )
