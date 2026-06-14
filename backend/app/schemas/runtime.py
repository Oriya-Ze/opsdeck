from pydantic import BaseModel


class RuntimeConfigResponse(BaseModel):
    app_env: str
    auth_mode: str
    prometheus_enabled: bool
    storage_type: str
