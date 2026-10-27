import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import UUID


class UserInstitutionRole(Base):
    __tablename__ = "user_institution_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    role_title = Column(String(100), nullable=True, default="Institution Representative")
    is_primary = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "institution_id", name="uq_user_institution"),
    )

    user = relationship("User", back_populates="institution_roles")
    institution = relationship("Institution", back_populates="user_roles")
