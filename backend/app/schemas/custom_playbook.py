import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CustomPlaybookBase(BaseModel):
    name: str = Field(..., max_length=100)
    label: str = Field(..., max_length=150)
    description: str | None = None
    playbook_content: str
    requires_sudo: bool = False
    timeout_seconds: int = Field(300, ge=30, le=3600)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        slug = value.strip().lower()
        if not _NAME_PATTERN.match(slug):
            raise ValueError("Name must be lowercase letters, numbers, and hyphens (e.g. my-playbook)")
        return slug

    @field_validator("playbook_content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        content = value.strip()
        if not content:
            raise ValueError("Playbook content cannot be empty")
        if "hosts:" not in content:
            raise ValueError("Playbook must include a 'hosts:' entry")
        return content


class CustomPlaybookCreate(CustomPlaybookBase):
    pass


class CustomPlaybookUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    playbook_content: str | None = None
    requires_sudo: bool | None = None
    timeout_seconds: int | None = Field(None, ge=30, le=3600)

    @field_validator("playbook_content")
    @classmethod
    def validate_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        content = value.strip()
        if not content:
            raise ValueError("Playbook content cannot be empty")
        if "hosts:" not in content:
            raise ValueError("Playbook must include a 'hosts:' entry")
        return content


class CustomPlaybookResponse(CustomPlaybookBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class PlaybookActionResponse(BaseModel):
    name: str
    label: str
    description: str
    requires_sudo: bool
    timeout_seconds: int
    source: str
    runner: str
    is_editable: bool
    custom_id: UUID | None = None
