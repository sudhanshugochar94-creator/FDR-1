import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.sql_types import JSONB, UUID


class FDRStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    EXTRACTED = "EXTRACTED"
    VALIDATED = "VALIDATED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    RENEWAL_PENDING = "RENEWAL_PENDING"
    RELEASED = "RELEASED"
    REJECTED = "REJECTED"
    CORRECTION_REQUESTED = "CORRECTION_REQUESTED"


class VerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    AWAITING_BANK_VERIFICATION = "AWAITING_BANK_VERIFICATION"


class FDRInstrument(Base):
    __tablename__ = "fdr_instruments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    internal_reference = Column(String(100), unique=True, nullable=False, index=True)
    application_number = Column(String(100), nullable=True)
    bank_name = Column(String(255), nullable=False, index=True)
    branch_name = Column(String(255), nullable=True)
    fdr_number = Column(String(100), nullable=False, index=True)
    deposit_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    issue_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False, index=True)
    status = Column(
        SAEnum(FDRStatus),
        default=FDRStatus.DRAFT,
        nullable=False,
        index=True,
    )
    verification_status = Column(
        SAEnum(VerificationStatus),
        default=VerificationStatus.PENDING,
        nullable=False,
    )
    review_priority_score = Column(Integer, default=0, nullable=False)
    review_priority_reasons = Column(JSONB, nullable=True)
    has_potential_duplicate = Column(Boolean, default=False, nullable=False)
    compliance_reference = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    submitted_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_reviewer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_fdr_institution_status", "institution_id", "status"),
        Index("ix_fdr_maturity_status", "maturity_date", "status"),
    )

    institution = relationship("Institution", back_populates="fdr_instruments")
    submitter = relationship("User", foreign_keys=[submitted_by], back_populates="submitted_fdrs")
    assigned_reviewer = relationship("User", foreign_keys=[assigned_reviewer_id], back_populates="assigned_fdrs")
    documents = relationship("FDRDocument", back_populates="fdr_instrument", cascade="all, delete-orphan")
    validation_findings = relationship("ValidationFinding", back_populates="fdr_instrument", cascade="all, delete-orphan")
    verification_records = relationship("VerificationRecord", back_populates="fdr_instrument", cascade="all, delete-orphan")
    review_assignments = relationship("ReviewAssignment", back_populates="fdr_instrument", cascade="all, delete-orphan")
    review_observations = relationship("ReviewObservation", back_populates="fdr_instrument", cascade="all, delete-orphan")
    duplicate_candidates_as_a = relationship(
        "DuplicateCandidate",
        foreign_keys="[DuplicateCandidate.fdr_instrument_a_id]",
        back_populates="instrument_a",
        passive_deletes=True,
    )
    duplicate_candidates_as_b = relationship(
        "DuplicateCandidate",
        foreign_keys="[DuplicateCandidate.fdr_instrument_b_id]",
        back_populates="instrument_b",
        passive_deletes=True,
    )
    parent_lifecycle_links = relationship(
        "LifecycleRelationship",
        foreign_keys="[LifecycleRelationship.parent_fdr_id]",
        back_populates="parent_fdr",
    )
    child_lifecycle_links = relationship(
        "LifecycleRelationship",
        foreign_keys="[LifecycleRelationship.child_fdr_id]",
        back_populates="child_fdr",
    )
    renewal_requests_as_original = relationship(
        "RenewalRequest",
        foreign_keys="[RenewalRequest.original_fdr_id]",
        back_populates="original_fdr",
    )
    renewal_requests_as_new = relationship(
        "RenewalRequest",
        foreign_keys="[RenewalRequest.new_fdr_id]",
        back_populates="new_fdr",
    )
    release_requests = relationship(
        "ReleaseRequest",
        back_populates="fdr_instrument",
        cascade="all, delete-orphan",
    )
