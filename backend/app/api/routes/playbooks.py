from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.custom_playbook import (
    CustomPlaybookCreate,
    CustomPlaybookResponse,
    CustomPlaybookUpdate,
    PlaybookActionResponse,
)
from app.services.ansible_runner import BUILTIN_ACTIONS, get_action_catalog, is_ansible_available
from app.services.playbook_service import (
    create_custom_playbook,
    delete_custom_playbook,
    get_custom_playbook,
    list_custom_playbooks,
    update_custom_playbook,
)

router = APIRouter(prefix="/playbooks", tags=["Playbooks"])


def _to_action_response(action, runner: str) -> PlaybookActionResponse:
    return PlaybookActionResponse(
        name=action.name,
        label=action.label,
        description=action.description,
        requires_sudo=action.requires_sudo,
        timeout_seconds=action.timeout_seconds,
        source=action.source,
        runner=runner,
        is_editable=action.source == "custom",
        custom_id=action.custom_id,
    )


@router.get("/actions", response_model=list[PlaybookActionResponse])
def list_all_playbook_actions(db: Session = Depends(get_db)):
    runner = "ansible" if is_ansible_available() else "shell"
    return [_to_action_response(action, runner) for action in get_action_catalog(db)]


@router.get("/builtin/list", response_model=list[PlaybookActionResponse])
def list_builtin_playbooks():
    runner = "ansible" if is_ansible_available() else "shell"
    return [_to_action_response(action, runner) for action in BUILTIN_ACTIONS]


@router.get("", response_model=list[CustomPlaybookResponse])
def list_playbooks(db: Session = Depends(get_db)):
    return list_custom_playbooks(db)


@router.post("", response_model=CustomPlaybookResponse, status_code=status.HTTP_201_CREATED)
def create_playbook(data: CustomPlaybookCreate, db: Session = Depends(get_db)):
    try:
        return create_custom_playbook(db, data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{playbook_id}", response_model=CustomPlaybookResponse)
def get_playbook(playbook_id: UUID, db: Session = Depends(get_db)):
    row = get_custom_playbook(db, playbook_id)
    if not row:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return row


@router.put("/{playbook_id}", response_model=CustomPlaybookResponse)
def update_playbook(playbook_id: UUID, data: CustomPlaybookUpdate, db: Session = Depends(get_db)):
    row = get_custom_playbook(db, playbook_id)
    if not row:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return update_custom_playbook(db, row, data.model_dump(exclude_unset=True))


@router.delete("/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_playbook(playbook_id: UUID, db: Session = Depends(get_db)):
    row = get_custom_playbook(db, playbook_id)
    if not row:
        raise HTTPException(status_code=404, detail="Playbook not found")
    delete_custom_playbook(db, row)
