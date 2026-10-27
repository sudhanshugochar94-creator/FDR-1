from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.deps import ensure_fdr_institution_access, get_current_user, require_role
from app.core.exceptions import ForbiddenException, NotFoundException
from app.database import get_db
from app.models.audit import AuditEvent
from app.models.duplicate import DuplicateCandidate, DuplicateStatus
from app.models.fdr import FDRInstrument, FDRStatus, VerificationStatus
from app.models.lifecycle import (
    LifecycleRelationship,
    LifecycleRelationshipType,
    ReleaseRequest,
    ReleaseStatus,
    RenewalRequest,
    RenewalStatus,
)
from app.models.notification import Notification, NotificationType
from app.models.review import ReviewObservation, ReviewObservationType
from app.models.user import User, UserRole
from app.models.verification import VerificationRecord, VerificationResult, VerificationType
from app.schemas.common import SuccessResponse
from app.schemas.fdr import (
    DuplicateCandidateBrief,
    ReleaseRequestBrief,
    RenewalRequestBrief,
    ReviewObservationBrief,
    VerificationRecordBrief,
)

router = APIRouter(tags=["Reviews, Verification & Lifecycle"])


# --- Schemas ---
class CreateObservationRequest(BaseModel):
    observation_type: ReviewObservationType = ReviewObservationType.NOTE
    content: str = Field(..., min_length=2)


class CreateVerificationRequest(BaseModel):
    verification_type: VerificationType = VerificationType.DOCUMENT_CHECK
    result: VerificationResult = VerificationResult.VERIFIED
    notes: Optional[str] = None
    evidence_summary: Optional[str] = None


class ResolveDuplicateRequest(BaseModel):
    status: DuplicateStatus
    review_notes: str = Field(..., min_length=2)


class CreateRenewalRequest(BaseModel):
    new_fdr_id: Optional[UUID] = None
    notes: Optional[str] = None


class CreateReleaseRequest(BaseModel):
    reason: str = Field(..., min_length=10)
    supporting_documents: Optional[Any] = None


class ApproverDecisionRequest(BaseModel):
    approved: bool
    notes: Optional[str] = None


# --- Endpoints ---

@router.post("/fdrs/{fdr_id}/observations", response_model=ReviewObservationBrief, status_code=status.HTTP_201_CREATED)
async def add_observation(
    fdr_id: UUID,
    payload: CreateObservationRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.REVIEWER, UserRole.APPROVING_AUTHORITY)),
    db: AsyncSession = Depends(get_db),
) -> ReviewObservationBrief:
    stmt = select(FDRInstrument).where(FDRInstrument.id == fdr_id)
    fdr = (await db.execute(stmt)).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR instrument {fdr_id} not found")

    obs = ReviewObservation(
        fdr_instrument_id=fdr.id,
        observer_id=current_user.id,
        observation_type=payload.observation_type,
        content=payload.content,
    )
    db.add(obs)

    # If it's a correction request, transition FDR status and notify submitter
    if payload.observation_type == ReviewObservationType.CORRECTION_REQUEST:
        fdr.status = FDRStatus.CORRECTION_REQUESTED
        if fdr.submitted_by:
            notif = Notification(
                user_id=fdr.submitted_by,
                title=f"Correction Requested: {fdr.internal_reference}",
                message=payload.content,
                notification_type=NotificationType.CORRECTION_REQUESTED,
                entity_type="fdr_instrument",
                entity_id=fdr.id,
            )
            db.add(notif)

    audit = AuditEvent(
        user_id=current_user.id,
        role=current_user.role.value,
        action="REVIEW_OBSERVATION_ADDED",
        entity_type="ReviewObservation",
        entity_id=obs.id,
        after_values={"type": payload.observation_type.value, "content": payload.content},
        reason="Review observation logged",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(obs)

    return ReviewObservationBrief.model_validate(obs)


@router.post("/fdrs/{fdr_id}/verify", response_model=VerificationRecordBrief, status_code=status.HTTP_201_CREATED)
async def record_verification(
    fdr_id: UUID,
    payload: CreateVerificationRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.REVIEWER, UserRole.APPROVING_AUTHORITY)),
    db: AsyncSession = Depends(get_db),
) -> VerificationRecordBrief:
    stmt = select(FDRInstrument).where(FDRInstrument.id == fdr_id)
    fdr = (await db.execute(stmt)).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR instrument {fdr_id} not found")

    rec = VerificationRecord(
        fdr_instrument_id=fdr.id,
        verified_by=current_user.id,
        verification_type=payload.verification_type,
        result=payload.result,
        notes=payload.notes,
        evidence_summary=payload.evidence_summary,
    )
    db.add(rec)

    if payload.result == VerificationResult.VERIFIED:
        fdr.verification_status = VerificationStatus.VERIFIED
        fdr.status = FDRStatus.ACTIVE
        fdr.review_priority_score = max(0, fdr.review_priority_score - 40)
    elif payload.result == VerificationResult.REJECTED:
        fdr.verification_status = VerificationStatus.REJECTED
        fdr.status = FDRStatus.REJECTED
    elif payload.result == VerificationResult.NEEDS_INFO:
        fdr.status = FDRStatus.CORRECTION_REQUESTED

    audit = AuditEvent(
        user_id=current_user.id,
        role=current_user.role.value,
        action="FDR_VERIFIED",
        entity_type="VerificationRecord",
        entity_id=rec.id,
        after_values={"result": payload.result.value, "notes": payload.notes},
        reason=f"Verification status set to {payload.result.value}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(rec)

    return VerificationRecordBrief(
        id=rec.id,
        verified_by=rec.verified_by,
        verifier_name=current_user.full_name,
        verification_type=rec.verification_type.value,
        result=rec.result.value,
        notes=rec.notes,
        evidence_summary=rec.evidence_summary,
        created_at=rec.created_at,
    )


@router.post("/duplicates/{candidate_id}/resolve", response_model=DuplicateCandidateBrief)
async def resolve_duplicate(
    candidate_id: UUID,
    payload: ResolveDuplicateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.REVIEWER)),
    db: AsyncSession = Depends(get_db),
) -> DuplicateCandidateBrief:
    stmt = select(DuplicateCandidate).where(DuplicateCandidate.id == candidate_id)
    cand = (await db.execute(stmt)).scalars().first()
    if not cand:
        raise NotFoundException(f"Duplicate candidate {candidate_id} not found")

    cand.status = payload.status
    cand.review_notes = payload.review_notes
    cand.reviewed_by = current_user.id
    cand.resolved_at = datetime.utcnow()

    # If false positive, check if remaining candidates exist for instrument A
    if payload.status == DuplicateStatus.FALSE_POSITIVE:
        other_stmt = select(DuplicateCandidate).where(
            DuplicateCandidate.fdr_instrument_a_id == cand.fdr_instrument_a_id,
            DuplicateCandidate.id != cand.id,
            DuplicateCandidate.status != DuplicateStatus.FALSE_POSITIVE,
        )
        remaining = (await db.execute(other_stmt)).scalars().first()
        if not remaining:
            fdr_stmt = select(FDRInstrument).where(FDRInstrument.id == cand.fdr_instrument_a_id)
            fdr_a = (await db.execute(fdr_stmt)).scalars().first()
            if fdr_a:
                fdr_a.has_potential_duplicate = False

    audit = AuditEvent(
        user_id=current_user.id,
        role=current_user.role.value,
        action="DUPLICATE_RESOLVED",
        entity_type="DuplicateCandidate",
        entity_id=cand.id,
        after_values={"status": payload.status.value, "notes": payload.review_notes},
        reason="Duplicate candidate reviewed",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(cand)

    return DuplicateCandidateBrief.model_validate(cand)


@router.post("/fdrs/{fdr_id}/renewal-request", response_model=RenewalRequestBrief, status_code=status.HTTP_201_CREATED)
async def request_renewal(
    fdr_id: UUID,
    payload: CreateRenewalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RenewalRequestBrief:
    stmt = select(FDRInstrument).where(FDRInstrument.id == fdr_id)
    fdr = (await db.execute(stmt)).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR instrument {fdr_id} not found")
    await ensure_fdr_institution_access(fdr=fdr, user=current_user, db=db)

    fdr.status = FDRStatus.RENEWAL_PENDING

    req = RenewalRequest(
        original_fdr_id=fdr.id,
        new_fdr_id=payload.new_fdr_id,
        status=RenewalStatus.PENDING,
        requested_by=current_user.id,
        review_notes=payload.notes,
    )
    db.add(req)

    if payload.new_fdr_id:
        new_fdr_stmt = select(FDRInstrument).where(FDRInstrument.id == payload.new_fdr_id)
        new_fdr = (await db.execute(new_fdr_stmt)).scalars().first()
        if not new_fdr:
            raise NotFoundException(f"FDR instrument {payload.new_fdr_id} not found")
        await ensure_fdr_institution_access(fdr=new_fdr, user=current_user, db=db)
        link = LifecycleRelationship(
            parent_fdr_id=fdr.id,
            child_fdr_id=payload.new_fdr_id,
            relationship_type=LifecycleRelationshipType.RENEWAL,
            notes=payload.notes,
            created_by=current_user.id,
        )
        db.add(link)

    await db.commit()
    await db.refresh(req)
    return RenewalRequestBrief.model_validate(req)


@router.post("/fdrs/{fdr_id}/release-request", response_model=ReleaseRequestBrief, status_code=status.HTTP_201_CREATED)
async def request_release(
    fdr_id: UUID,
    payload: CreateReleaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReleaseRequestBrief:
    stmt = select(FDRInstrument).where(FDRInstrument.id == fdr_id)
    fdr = (await db.execute(stmt)).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR instrument {fdr_id} not found")
    await ensure_fdr_institution_access(fdr=fdr, user=current_user, db=db)

    fdr.status = FDRStatus.UNDER_REVIEW

    req = ReleaseRequest(
        fdr_instrument_id=fdr.id,
        reason=payload.reason,
        supporting_documents=payload.supporting_documents,
        status=ReleaseStatus.PENDING,
        requested_by=current_user.id,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return ReleaseRequestBrief.model_validate(req)


@router.post("/release-requests/{request_id}/decision", response_model=ReleaseRequestBrief)
async def approve_or_reject_release(
    request_id: UUID,
    payload: ApproverDecisionRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.APPROVING_AUTHORITY)),
    db: AsyncSession = Depends(get_db),
) -> ReleaseRequestBrief:
    stmt = (
        select(ReleaseRequest)
        .options(selectinload(ReleaseRequest.fdr_instrument))
        .where(ReleaseRequest.id == request_id)
    )
    req = (await db.execute(stmt)).scalars().first()
    if not req:
        raise NotFoundException(f"Release request {request_id} not found")

    req.approved_by = current_user.id
    req.approver_notes = payload.notes
    req.decision_date = datetime.utcnow()

    if payload.approved:
        req.status = ReleaseStatus.APPROVED
        if req.fdr_instrument:
            req.fdr_instrument.status = FDRStatus.RELEASED
    else:
        req.status = ReleaseStatus.REJECTED

    await db.commit()
    await db.refresh(req)
    return ReleaseRequestBrief.model_validate(req)
