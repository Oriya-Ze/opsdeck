from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://opsdeck:opsdeck@postgres:5432/opsdeck"
    API_V1_PREFIX: str = "/api"
    APP_NAME: str = "OpsDeck"
    APP_VERSION: str = "0.1.0"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    # Fernet key for encrypting SSH private keys at rest (generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    ENCRYPTION_KEY: str = "opsdeck-dev-key-change-in-production-32b="

    class Config:
        env_file = ".env"


settings = Settings()
