from datetime import datetime

from pydantic import BaseModel, Field


class SshSettingsResponse(BaseModel):
    configured: bool
    ssh_user: str | None = None
    key_fingerprint: str | None = None
    public_key: str | None = None
    updated_at: datetime | None = None


class SshSettingsSave(BaseModel):
    ssh_user: str = Field(..., min_length=1, max_length=64)
    private_key: str | None = None
    public_key: str | None = None


class SshTestRequest(BaseModel):
    host: str
    port: int = 22
    ssh_user: str | None = None
    private_key: str | None = None


class SshTestResponse(BaseModel):
    success: bool
    message: str
    response_time_ms: int | None = None
    output: str | None = None


class SshGenerateResponse(BaseModel):
    public_key: str
    private_key: str
    fingerprint: str
    instructions: str
