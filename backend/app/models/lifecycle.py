import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import JSONB, UUID


class LifecycleRelationshipType(str, enum.Enum):
    RENEWAL = "RENEWAL"
    REPLACEMENT = "REPLACEMENT"


class RenewalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"


class ReleaseStatus(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LifecycleRelationship(Base):
    __tablename__ = "lifecycle_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_fdr_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    child_fdr_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type = Column(SAEnum(LifecycleRelationshipType), nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    parent_fdr = relationship(
        "FDRInstrument",
        foreign_keys=[parent_fdr_id],
        back_populates="parent_lifecycle_links",
    )
    child_fdr = relationship(
        "FDRInstrument",
        foreign_keys=[child_fdr_id],
        back_populates="child_lifecycle_links",
    )
    creator = relationship("User", foreign_keys=[created_by])


class RenewalRequest(Base):
    __tablename__ = "renewal_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_fdr_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    new_fdr_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(
        SAEnum(RenewalStatus),
        default=RenewalStatus.PENDING,
        nullable=False,
    )
    requested_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    original_fdr = relationship(
        "FDRInstrument",
        foreign_keys=[original_fdr_id],
        back_populates="renewal_requests_as_original",
    )
    new_fdr = relationship(
        "FDRInstrument",
        foreign_keys=[new_fdr_id],
        back_populates="renewal_requests_as_new",
    )
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class ReleaseRequest(Base):
    __tablename__ = "release_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fdr_instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason = Column(Text, nullable=False)
    supporting_documents = Column(JSONB, nullable=True)
    status = Column(
        SAEnum(ReleaseStatus),
        default=ReleaseStatus.PENDING,
        nullable=False,
    )
    requested_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewer_notes = Column(Text, nullable=True)
    approved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approver_notes = Column(Text, nullable=True)
    decision_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    fdr_instrument = relationship("FDRInstrument", back_populates="release_requests")
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    approver = relationship("User", foreign_keys=[approved_by])
