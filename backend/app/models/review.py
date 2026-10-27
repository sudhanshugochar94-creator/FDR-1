import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import UUID


class ReviewAssignmentStatus(str, enum.Enum):
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class ReviewObservationType(str, enum.Enum):
    NOTE = "NOTE"
    CORRECTION_REQUEST = "CORRECTION_REQUEST"
    ADDITIONAL_DOCS_NEEDED = "ADDITIONAL_DOCS_NEEDED"
    CLARIFICATION = "CLARIFICATION"


class ReviewAssignment(Base):
    __tablename__ = "review_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fdr_instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(
        SAEnum(ReviewAssignmentStatus),
        default=ReviewAssignmentStatus.ASSIGNED,
        nullable=False,
    )
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    fdr_instrument = relationship("FDRInstrument", back_populates="review_assignments")
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="review_assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])


class ReviewObservation(Base):
    __tablename__ = "review_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fdr_instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_type = Column(
        SAEnum(ReviewObservationType),
        default=ReviewObservationType.NOTE,
        nullable=False,
    )
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fdr_instrument = relationship("FDRInstrument", back_populates="review_observations")
    observer = relationship("User", foreign_keys=[observer_id])
