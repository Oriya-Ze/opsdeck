import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import NodeEnvironment, NodeRole, NodeStatus


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    ssh_port: Mapped[int] = mapped_column(Integer, default=22)
    ssh_user: Mapped[str | None] = mapped_column(String(64), nullable=True)
    os_name: Mapped[str] = mapped_column(String(100), nullable=False)
    environment: Mapped[str] = mapped_column(String(20), default=NodeEnvironment.LOCAL.value)
    role: Mapped[str] = mapped_column(String(30), default=NodeRole.SERVER.value)
    status: Mapped[str] = mapped_column(String(20), default=NodeStatus.UNKNOWN.value)
    cpu_usage: Mapped[float] = mapped_column(Float, default=0.0)
    ram_usage: Mapped[float] = mapped_column(Float, default=0.0)
    disk_usage: Mapped[float] = mapped_column(Float, default=0.0)
    uptime: Mapped[str] = mapped_column(String(100), default="unknown")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_sync_containers: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    services = relationship("Service", back_populates="node", cascade="all, delete-orphan")
    containers = relationship("Container", back_populates="node", cascade="all, delete-orphan")
    workloads = relationship("Workload", back_populates="node")
