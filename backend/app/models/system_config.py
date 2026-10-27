import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import JSONB, UUID


class SystemConfiguration(Base):
    __tablename__ = "system_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    updater = relationship("User", foreign_keys=[updated_by])
