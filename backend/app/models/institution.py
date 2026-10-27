import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import UUID


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(500), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    address = Column(String(1000), nullable=True)
    city = Column(String(200), nullable=True)
    state = Column(String(200), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user_roles = relationship(
        "UserInstitutionRole",
        back_populates="institution",
        cascade="all, delete-orphan",
    )
    fdr_instruments = relationship(
        "FDRInstrument",
        back_populates="institution",
        cascade="all, delete-orphan",
    )
