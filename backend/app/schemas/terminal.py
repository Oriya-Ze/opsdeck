from uuid import UUID

from pydantic import BaseModel


class TerminalTargetOption(BaseModel):
    id: str
    label: str
    description: str
    target: str
    node_id: UUID | None = None


class TerminalOptionsResponse(BaseModel):
    targets: list[TerminalTargetOption]
