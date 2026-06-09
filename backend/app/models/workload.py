import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import WorkloadKind, WorkloadStatus


class Workload(Base):
    __tablename__ = "workloads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    namespace: Mapped[str] = mapped_column(String(100), default="default")
    kind: Mapped[str] = mapped_column(String(30), default=WorkloadKind.DEPLOYMENT.value)
    cluster_name: Mapped[str] = mapped_column(String(100), default="k3s-local")
    node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("nodes.id"), nullable=True)
    replicas: Mapped[int] = mapped_column(Integer, default=1)
    ready_replicas: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=WorkloadStatus.UNKNOWN.value)
    image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    node = relationship("Node", back_populates="workloads")
