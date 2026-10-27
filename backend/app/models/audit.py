import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import JSONB, UUID


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    role = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    before_values = Column(JSONB, nullable=True)
    after_values = Column(JSONB, nullable=True)
    reason = Column(Text, nullable=True)
    correlation_id = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_user_action", "user_id", "action"),
    )

    user = relationship("User", foreign_keys=[user_id], back_populates="audit_events")
