import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import UUID


class NotificationType(str, enum.Enum):
    MATURITY_REMINDER = "MATURITY_REMINDER"
    REVIEW_NEEDED = "REVIEW_NEEDED"
    CORRECTION_REQUESTED = "CORRECTION_REQUESTED"
    STATUS_CHANGE = "STATUS_CHANGE"
    DUPLICATE_FOUND = "DUPLICATE_FOUND"
    SYSTEM = "SYSTEM"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(SAEnum(NotificationType), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="notifications")
