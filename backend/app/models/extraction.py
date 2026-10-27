import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import JSONB, UUID


class ExtractionMethod(str, enum.Enum):
    TEXT_EXTRACTION = "TEXT_EXTRACTION"
    OCR = "OCR"
    AI_ASSISTED = "AI_ASSISTED"


class ExtractionResult(Base):
    __tablename__ = "extraction_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extraction_method = Column(SAEnum(ExtractionMethod), nullable=False)
    raw_text = Column(Text, nullable=True)
    extracted_fields = Column(JSONB, nullable=True)
    confidence_scores = Column(JSONB, nullable=True)
    ai_model_used = Column(String(100), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("FDRDocument", back_populates="extractions")
