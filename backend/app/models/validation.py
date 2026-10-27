import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import UUID


class FindingType(str, enum.Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    MISSING_IN_FORM = "MISSING_IN_FORM"
    MISSING_IN_DOCUMENT = "MISSING_IN_DOCUMENT"
    FORMAT_ERROR = "FORMAT_ERROR"


class FindingSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ValidationFinding(Base):
    __tablename__ = "validation_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fdr_instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name = Column(String(100), nullable=False)
    submitted_value = Column(String(500), nullable=True)
    extracted_value = Column(String(500), nullable=True)
    finding_type = Column(SAEnum(FindingType), nullable=False)
    severity = Column(SAEnum(FindingSeverity), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fdr_instrument = relationship("FDRInstrument", back_populates="validation_findings")
