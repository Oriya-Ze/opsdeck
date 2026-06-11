from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SyncSettings(Base):
    """Singleton row (id=1) for background sync configuration."""

    __tablename__ = "sync_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    containers_auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    containers_sync_interval_seconds: Mapped[int] = mapped_column(Integer, default=300)
    last_auto_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_auto_sync_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
