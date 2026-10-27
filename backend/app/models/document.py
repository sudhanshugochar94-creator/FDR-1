import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import UUID


class DocumentUploadType(str, enum.Enum):
    ORIGINAL = "ORIGINAL"
    RENEWAL = "RENEWAL"
    SUPPORTING = "SUPPORTING"


class FDRDocument(Base):
    __tablename__ = "fdr_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fdr_instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_hash_sha256 = Column(String(64), nullable=False, index=True)
    upload_type = Column(
        SAEnum(DocumentUploadType),
        default=DocumentUploadType.ORIGINAL,
        nullable=False,
    )
    uploaded_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fdr_instrument = relationship("FDRInstrument", back_populates="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by], back_populates="uploaded_documents")
    extractions = relationship("ExtractionResult", back_populates="document", cascade="all, delete-orphan")
