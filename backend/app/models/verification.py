import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import UUID


class VerificationType(str, enum.Enum):
    DOCUMENT_CHECK = "DOCUMENT_CHECK"
    BANK_CONFIRMATION = "BANK_CONFIRMATION"
    FIELD_VERIFICATION = "FIELD_VERIFICATION"


class VerificationResult(str, enum.Enum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    NEEDS_INFO = "NEEDS_INFO"


class VerificationRecord(Base):
    __tablename__ = "verification_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fdr_instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    verified_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    verification_type = Column(SAEnum(VerificationType), nullable=False)
    result = Column(SAEnum(VerificationResult), nullable=False)
    notes = Column(Text, nullable=True)
    evidence_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fdr_instrument = relationship("FDRInstrument", back_populates="verification_records")
    verifier = relationship("User", foreign_keys=[verified_by])
