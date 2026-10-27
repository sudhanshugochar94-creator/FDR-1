from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.document import DocumentUploadType
from app.models.duplicate import DuplicateStatus
from app.models.extraction import ExtractionMethod
from app.models.fdr import FDRStatus, VerificationStatus
from app.models.lifecycle import LifecycleRelationshipType, ReleaseStatus, RenewalStatus
from app.models.review import ReviewAssignmentStatus, ReviewObservationType
from app.models.validation import FindingSeverity, FindingType


class FDRCreateRequest(BaseModel):
    institution_id: Optional[UUID] = None  # Auto-filled for institution_user
    internal_reference: Optional[str] = Field(None, max_length=100)
    application_number: Optional[str] = Field(None, max_length=100)
    bank_name: str = Field(..., min_length=2, max_length=255)
    branch_name: Optional[str] = Field(None, max_length=255)
    fdr_number: str = Field(..., min_length=2, max_length=100)
    deposit_amount: Decimal = Field(..., gt=0)
    currency: str = Field("INR", max_length=10)
    issue_date: date
    maturity_date: date
    compliance_reference: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


class FDRUpdateRequest(BaseModel):
    application_number: Optional[str] = None
    bank_name: Optional[str] = None
    branch_name: Optional[str] = None
    fdr_number: Optional[str] = None
    deposit_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    issue_date: Optional[date] = None
    maturity_date: Optional[date] = None
    compliance_reference: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[FDRStatus] = None


# Sub-schemas for Detail View
class DocumentBrief(BaseModel):
    id: UUID
    original_filename: str
    stored_filename: str
    file_size: int
    mime_type: str
    file_hash_sha256: str
    upload_type: DocumentUploadType
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExtractionBrief(BaseModel):
    id: UUID
    document_id: UUID
    extraction_method: ExtractionMethod
    raw_text: Optional[str] = None
    extracted_fields: Optional[Any] = None
    confidence_scores: Optional[Any] = None
    ai_model_used: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ValidationFindingBrief(BaseModel):
    id: UUID
    field_name: str
    submitted_value: Optional[str] = None
    extracted_value: Optional[str] = None
    finding_type: FindingType
    severity: FindingSeverity
    description: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DuplicateCandidateBrief(BaseModel):
    id: UUID
    fdr_instrument_a_id: UUID
    fdr_instrument_b_id: UUID
    match_score: float
    match_reasons: Optional[Any] = None
    matching_fields: Optional[Any] = None
    differing_fields: Optional[Any] = None
    file_hash_match: bool
    status: DuplicateStatus
    review_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class VerificationRecordBrief(BaseModel):
    id: UUID
    verified_by: UUID
    verifier_name: Optional[str] = None
    verification_type: str
    result: str
    notes: Optional[str] = None
    evidence_summary: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReviewObservationBrief(BaseModel):
    id: UUID
    observer_id: UUID
    observer_name: Optional[str] = None
    observation_type: ReviewObservationType
    content: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LifecycleRelationshipBrief(BaseModel):
    id: UUID
    parent_fdr_id: UUID
    child_fdr_id: UUID
    relationship_type: LifecycleRelationshipType
    notes: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RenewalRequestBrief(BaseModel):
    id: UUID
    original_fdr_id: UUID
    new_fdr_id: Optional[UUID] = None
    status: RenewalStatus
    requested_by: UUID
    review_notes: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReleaseRequestBrief(BaseModel):
    id: UUID
    fdr_instrument_id: UUID
    reason: str
    supporting_documents: Optional[Any] = None
    status: ReleaseStatus
    requested_by: UUID
    reviewer_notes: Optional[str] = None
    approved_by: Optional[UUID] = None
    approver_notes: Optional[str] = None
    decision_date: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class FDRListItemResponse(BaseModel):
    id: UUID
    institution_id: UUID
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    internal_reference: str
    application_number: Optional[str] = None
    bank_name: str
    branch_name: Optional[str] = None
    fdr_number: str
    deposit_amount: Decimal
    currency: str
    issue_date: date
    maturity_date: date
    status: FDRStatus
    verification_status: VerificationStatus
    review_priority_score: int
    has_potential_duplicate: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FDRDetailResponse(FDRListItemResponse):
    compliance_reference: Optional[str] = None
    notes: Optional[str] = None
    review_priority_reasons: Optional[Any] = None
    submitted_by: Optional[UUID] = None
    assigned_reviewer_id: Optional[UUID] = None
    documents: List[DocumentBrief] = []
    validation_findings: List[ValidationFindingBrief] = []
    verification_records: List[VerificationRecordBrief] = []
    review_observations: List[ReviewObservationBrief] = []
    duplicate_candidates: List[DuplicateCandidateBrief] = []
    parent_lifecycle_links: List[LifecycleRelationshipBrief] = []
    child_lifecycle_links: List[LifecycleRelationshipBrief] = []
    renewal_requests: List[RenewalRequestBrief] = []
    release_requests: List[ReleaseRequestBrief] = []

    model_config = ConfigDict(from_attributes=True)
