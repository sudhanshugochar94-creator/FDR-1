import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, String
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import UUID


class UserRole(str, enum.Enum):
    INSTITUTION_USER = "institution_user"
    REVIEWER = "reviewer"
    APPROVING_AUTHORITY = "approving_authority"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    institution_roles = relationship(
        "UserInstitutionRole",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    review_assignments = relationship(
        "ReviewAssignment",
        back_populates="reviewer",
        foreign_keys="[ReviewAssignment.reviewer_id]",
    )
    audit_events = relationship(
        "AuditEvent",
        back_populates="user",
        foreign_keys="[AuditEvent.user_id]",
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    submitted_fdrs = relationship(
        "FDRInstrument",
        back_populates="submitter",
        foreign_keys="[FDRInstrument.submitted_by]",
    )
    assigned_fdrs = relationship(
        "FDRInstrument",
        back_populates="assigned_reviewer",
        foreign_keys="[FDRInstrument.assigned_reviewer_id]",
    )
    uploaded_documents = relationship(
        "FDRDocument",
        back_populates="uploader",
        foreign_keys="[FDRDocument.uploaded_by]",
    )
