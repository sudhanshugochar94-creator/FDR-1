import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import JSONB, UUID


class DuplicateStatus(str, enum.Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    ESCALATED = "ESCALATED"


class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fdr_instrument_a_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fdr_instrument_b_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_score = Column(Float, nullable=False)
    match_reasons = Column(JSONB, nullable=True)
    matching_fields = Column(JSONB, nullable=True)
    differing_fields = Column(JSONB, nullable=True)
    file_hash_match = Column(Boolean, default=False, nullable=False)
    status = Column(
        SAEnum(DuplicateStatus),
        default=DuplicateStatus.PENDING,
        nullable=False,
    )
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    instrument_a = relationship(
        "FDRInstrument",
        foreign_keys=[fdr_instrument_a_id],
        back_populates="duplicate_candidates_as_a",
    )
    instrument_b = relationship(
        "FDRInstrument",
        foreign_keys=[fdr_instrument_b_id],
        back_populates="duplicate_candidates_as_b",
    )
    reviewer = relationship("User", foreign_keys=[reviewed_by])
