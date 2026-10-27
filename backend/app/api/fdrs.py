import math
import random
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.deps import get_current_institution, get_current_user
from app.core.exceptions import ForbiddenException, NotFoundException
from app.database import get_db
from app.models.audit import AuditEvent
from app.models.fdr import FDRInstrument, FDRStatus, VerificationStatus
from app.models.institution import Institution
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.fdr import (
    DocumentBrief,
    DuplicateCandidateBrief,
    FDRCreateRequest,
    FDRDetailResponse,
    FDRListItemResponse,
    FDRUpdateRequest,
    LifecycleRelationshipBrief,
    ReleaseRequestBrief,
    RenewalRequestBrief,
    ReviewObservationBrief,
    ValidationFindingBrief,
    VerificationRecordBrief,
)
from app.services.duplicate_service import check_and_flag_duplicates

router = APIRouter(prefix="/fdrs", tags=["FDR Management"])


def generate_internal_reference() -> str:
    year = datetime.utcnow().year
    rand_num = random.randint(1000, 9999)
    return f"FDR-{year}-{rand_num}"


@router.get("", response_model=PaginatedResponse[FDRListItemResponse])
async def list_fdrs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[FDRStatus] = Query(None, description="Filter by FDR status"),
    verification_status: Optional[VerificationStatus] = Query(None, description="Filter by verification status"),
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
    search: Optional[str] = Query(None, description="Search by FDR number, ref, or branch"),
    has_potential_duplicate: Optional[bool] = Query(None, description="Filter by duplicate flag"),
    min_amount: Optional[Decimal] = Query(None, ge=0),
    max_amount: Optional[Decimal] = Query(None, ge=0),
    institution_id: Optional[UUID] = Query(None, description="Filter by institution (Admin/Reviewer)"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[FDRListItemResponse]:
    # Determine tenant scoping
    scoped_inst_id: Optional[UUID] = None
    if current_user.role == UserRole.INSTITUTION_USER:
        inst = await get_current_institution(user=current_user, db=db)
        if not inst:
            raise ForbiddenException("User is not mapped to any valid institution")
        scoped_inst_id = inst.id
    elif institution_id:
        scoped_inst_id = institution_id

    conditions = []
    if scoped_inst_id:
        conditions.append(FDRInstrument.institution_id == scoped_inst_id)
    if status:
        conditions.append(FDRInstrument.status == status)
    if verification_status:
        conditions.append(FDRInstrument.verification_status == verification_status)
    if bank_name:
        conditions.append(FDRInstrument.bank_name.ilike(f"%{bank_name.strip()}%"))
    if has_potential_duplicate is not None:
        conditions.append(FDRInstrument.has_potential_duplicate == has_potential_duplicate)
    if min_amount is not None:
        conditions.append(FDRInstrument.deposit_amount >= min_amount)
    if max_amount is not None:
        conditions.append(FDRInstrument.deposit_amount <= max_amount)
    if search:
        search_term = f"%{search.strip()}%"
        conditions.append(
            or_(
                FDRInstrument.internal_reference.ilike(search_term),
                FDRInstrument.fdr_number.ilike(search_term),
                FDRInstrument.bank_name.ilike(search_term),
                FDRInstrument.branch_name.ilike(search_term),
                FDRInstrument.application_number.ilike(search_term),
            )
        )

    # Count total matching
    count_stmt = select(func.count(FDRInstrument.id)).where(*conditions)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Build select query with relationship to Institution
    stmt = (
        select(FDRInstrument)
        .options(selectinload(FDRInstrument.institution))
        .where(*conditions)
    )

    # Sorting
    sort_column = getattr(FDRInstrument, sort_by, FDRInstrument.created_at)
    if sort_order == "desc":
        stmt = stmt.order_by(desc(sort_column))
    else:
        stmt = stmt.order_by(sort_column)

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await db.execute(stmt)
    records = result.scalars().all()

    items = []
    for r in records:
        inst_name = r.institution.name if r.institution else None
        inst_code = r.institution.code if r.institution else None
        items.append(
            FDRListItemResponse(
                id=r.id,
                institution_id=r.institution_id,
                institution_name=inst_name,
                institution_code=inst_code,
                internal_reference=r.internal_reference,
                application_number=r.application_number,
                bank_name=r.bank_name,
                branch_name=r.branch_name,
                fdr_number=r.fdr_number,
                deposit_amount=r.deposit_amount,
                currency=r.currency,
                issue_date=r.issue_date,
                maturity_date=r.maturity_date,
                status=r.status,
                verification_status=r.verification_status,
                review_priority_score=r.review_priority_score,
                has_potential_duplicate=r.has_potential_duplicate,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )

    pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{fdr_id}", response_model=FDRDetailResponse)
async def get_fdr(
    fdr_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FDRDetailResponse:
    stmt = (
        select(FDRInstrument)
        .options(
            selectinload(FDRInstrument.institution),
            selectinload(FDRInstrument.documents),
            selectinload(FDRInstrument.validation_findings),
            selectinload(FDRInstrument.verification_records),
            selectinload(FDRInstrument.review_observations),
            selectinload(FDRInstrument.duplicate_candidates_as_a),
            selectinload(FDRInstrument.duplicate_candidates_as_b),
            selectinload(FDRInstrument.parent_lifecycle_links),
            selectinload(FDRInstrument.child_lifecycle_links),
            selectinload(FDRInstrument.renewal_requests_as_original),
            selectinload(FDRInstrument.renewal_requests_as_new),
            selectinload(FDRInstrument.release_requests),
        )
        .where(FDRInstrument.id == fdr_id)
    )
    result = await db.execute(stmt)
    fdr = result.scalars().first()

    if not fdr:
        raise NotFoundException(f"FDR instrument with ID {fdr_id} not found")

    # Scope check for institution users
    if current_user.role == UserRole.INSTITUTION_USER:
        inst = await get_current_institution(user=current_user, db=db)
        if not inst or fdr.institution_id != inst.id:
            raise ForbiddenException("You do not have permission to view this FDR")

    # Combine duplicate candidates from both sides (A and B)
    all_dup_candidates = list(fdr.duplicate_candidates_as_a) + list(fdr.duplicate_candidates_as_b)
    # Combine renewals
    all_renewals = list(fdr.renewal_requests_as_original) + list(fdr.renewal_requests_as_new)

    return FDRDetailResponse(
        id=fdr.id,
        institution_id=fdr.institution_id,
        institution_name=fdr.institution.name if fdr.institution else None,
        institution_code=fdr.institution.code if fdr.institution else None,
        internal_reference=fdr.internal_reference,
        application_number=fdr.application_number,
        bank_name=fdr.bank_name,
        branch_name=fdr.branch_name,
        fdr_number=fdr.fdr_number,
        deposit_amount=fdr.deposit_amount,
        currency=fdr.currency,
        issue_date=fdr.issue_date,
        maturity_date=fdr.maturity_date,
        status=fdr.status,
        verification_status=fdr.verification_status,
        review_priority_score=fdr.review_priority_score,
        has_potential_duplicate=fdr.has_potential_duplicate,
        compliance_reference=fdr.compliance_reference,
        notes=fdr.notes,
        review_priority_reasons=fdr.review_priority_reasons,
        submitted_by=fdr.submitted_by,
        assigned_reviewer_id=fdr.assigned_reviewer_id,
        created_at=fdr.created_at,
        updated_at=fdr.updated_at,
        documents=[DocumentBrief.model_validate(d) for d in fdr.documents],
        validation_findings=[ValidationFindingBrief.model_validate(vf) for vf in fdr.validation_findings],
        verification_records=[
            VerificationRecordBrief(
                id=vr.id,
                verified_by=vr.verified_by,
                verification_type=vr.verification_type.value if hasattr(vr.verification_type, "value") else str(vr.verification_type),
                result=vr.result.value if hasattr(vr.result, "value") else str(vr.result),
                notes=vr.notes,
                evidence_summary=vr.evidence_summary,
                created_at=vr.created_at,
            )
            for vr in fdr.verification_records
        ],
        review_observations=[ReviewObservationBrief.model_validate(ro) for ro in fdr.review_observations],
        duplicate_candidates=[DuplicateCandidateBrief.model_validate(dc) for dc in all_dup_candidates],
        parent_lifecycle_links=[LifecycleRelationshipBrief.model_validate(lc) for lc in fdr.parent_lifecycle_links],
        child_lifecycle_links=[LifecycleRelationshipBrief.model_validate(lc) for lc in fdr.child_lifecycle_links],
        renewal_requests=[RenewalRequestBrief.model_validate(rr) for rr in all_renewals],
        release_requests=[ReleaseRequestBrief.model_validate(rr) for rr in fdr.release_requests],
    )


@router.post("", response_model=FDRListItemResponse, status_code=status.HTTP_201_CREATED)
async def create_fdr(
    payload: FDRCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FDRListItemResponse:
    # Resolve target institution
    if current_user.role == UserRole.INSTITUTION_USER:
        inst = await get_current_institution(user=current_user, db=db)
        if not inst:
            raise ForbiddenException("User not associated with any institution")
        target_inst_id = inst.id
    else:
        if not payload.institution_id:
            raise HTTPException(status_code=400, detail="institution_id is required for administrative submission")
        target_inst_id = payload.institution_id

    # Check institution exists
    inst_stmt = select(Institution).where(Institution.id == target_inst_id)
    institution = (await db.execute(inst_stmt)).scalars().first()
    if not institution:
        raise NotFoundException(f"Institution with ID {target_inst_id} does not exist")

    # Generate internal ref if missing
    ref = payload.internal_reference.strip() if payload.internal_reference else generate_internal_reference()

    new_fdr = FDRInstrument(
        institution_id=target_inst_id,
        internal_reference=ref,
        application_number=payload.application_number,
        bank_name=payload.bank_name.strip(),
        branch_name=payload.branch_name.strip() if payload.branch_name else None,
        fdr_number=payload.fdr_number.strip(),
        deposit_amount=payload.deposit_amount,
        currency=payload.currency.strip().upper(),
        issue_date=payload.issue_date,
        maturity_date=payload.maturity_date,
        status=FDRStatus.SUBMITTED,
        verification_status=VerificationStatus.PENDING,
        review_priority_score=0,
        has_potential_duplicate=False,
        compliance_reference=payload.compliance_reference,
        notes=payload.notes,
        submitted_by=current_user.id,
    )
    db.add(new_fdr)
    await db.flush()

    await check_and_flag_duplicates(fdr=new_fdr, document=None, db=db)

    # Log audit event
    audit = AuditEvent(
        user_id=current_user.id,
        role=current_user.role.value,
        action="FDR_CREATED",
        entity_type="FDRInstrument",
        entity_id=new_fdr.id,
        timestamp=datetime.utcnow(),
        after_values={
            "internal_reference": new_fdr.internal_reference,
            "fdr_number": new_fdr.fdr_number,
            "deposit_amount": str(new_fdr.deposit_amount),
            "bank_name": new_fdr.bank_name,
        },
        reason="New FDR instrument submitted",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_fdr)

    return FDRListItemResponse(
        id=new_fdr.id,
        institution_id=new_fdr.institution_id,
        institution_name=institution.name,
        institution_code=institution.code,
        internal_reference=new_fdr.internal_reference,
        application_number=new_fdr.application_number,
        bank_name=new_fdr.bank_name,
        branch_name=new_fdr.branch_name,
        fdr_number=new_fdr.fdr_number,
        deposit_amount=new_fdr.deposit_amount,
        currency=new_fdr.currency,
        issue_date=new_fdr.issue_date,
        maturity_date=new_fdr.maturity_date,
        status=new_fdr.status,
        verification_status=new_fdr.verification_status,
        review_priority_score=new_fdr.review_priority_score,
        has_potential_duplicate=new_fdr.has_potential_duplicate,
        created_at=new_fdr.created_at,
        updated_at=new_fdr.updated_at,
    )


@router.patch("/{fdr_id}", response_model=FDRListItemResponse)
async def update_fdr(
    fdr_id: UUID,
    payload: FDRUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FDRListItemResponse:
    stmt = (
        select(FDRInstrument)
        .options(selectinload(FDRInstrument.institution))
        .where(FDRInstrument.id == fdr_id)
    )
    fdr = (await db.execute(stmt)).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR instrument {fdr_id} not found")

    # Access scoping
    if current_user.role == UserRole.INSTITUTION_USER:
        inst = await get_current_institution(user=current_user, db=db)
        if not inst or fdr.institution_id != inst.id:
            raise ForbiddenException("Permission denied")

    before_dict = {
        "bank_name": fdr.bank_name,
        "deposit_amount": str(fdr.deposit_amount),
        "status": fdr.status.value,
    }

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(fdr, field, val)

    fdr.updated_at = datetime.utcnow()

    # Log audit event
    audit = AuditEvent(
        user_id=current_user.id,
        role=current_user.role.value,
        action="FDR_UPDATED",
        entity_type="FDRInstrument",
        entity_id=fdr.id,
        timestamp=datetime.utcnow(),
        before_values=before_dict,
        after_values={k: str(v) for k, v in update_data.items()},
        reason="FDR attributes updated",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(fdr)

    return FDRListItemResponse(
        id=fdr.id,
        institution_id=fdr.institution_id,
        institution_name=fdr.institution.name if fdr.institution else None,
        institution_code=fdr.institution.code if fdr.institution else None,
        internal_reference=fdr.internal_reference,
        application_number=fdr.application_number,
        bank_name=fdr.bank_name,
        branch_name=fdr.branch_name,
        fdr_number=fdr.fdr_number,
        deposit_amount=fdr.deposit_amount,
        currency=fdr.currency,
        issue_date=fdr.issue_date,
        maturity_date=fdr.maturity_date,
        status=fdr.status,
        verification_status=fdr.verification_status,
        review_priority_score=fdr.review_priority_score,
        has_potential_duplicate=fdr.has_potential_duplicate,
        created_at=fdr.created_at,
        updated_at=fdr.updated_at,
    )


@router.delete("/{fdr_id}", response_model=SuccessResponse)
async def delete_fdr(
    fdr_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    stmt = select(FDRInstrument).where(FDRInstrument.id == fdr_id)
    fdr = (await db.execute(stmt)).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR instrument {fdr_id} not found")

    if current_user.role == UserRole.INSTITUTION_USER:
        inst = await get_current_institution(user=current_user, db=db)
        if not inst or fdr.institution_id != inst.id:
            raise ForbiddenException("Permission denied")
        if fdr.status not in [FDRStatus.DRAFT, FDRStatus.CORRECTION_REQUESTED]:
            raise ForbiddenException("Institution users can only delete Drafts or Correction Requested records")

    ref = fdr.internal_reference
    await db.delete(fdr)

    audit = AuditEvent(
        user_id=current_user.id,
        role=current_user.role.value,
        action="FDR_DELETED",
        entity_type="FDRInstrument",
        entity_id=fdr_id,
        timestamp=datetime.utcnow(),
        before_values={"internal_reference": ref},
        reason="FDR deleted",
    )
    db.add(audit)
    await db.commit()

    return SuccessResponse(message=f"FDR {ref} successfully deleted")
