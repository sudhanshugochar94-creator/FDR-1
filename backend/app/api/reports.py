"""Reports and Audit endpoints for compliance reporting and CSV exports."""

import csv
import io
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_institution, get_current_user, require_role
from app.core.exceptions import ForbiddenException
from app.database import get_db
from app.models.audit import AuditEvent
from app.models.duplicate import DuplicateCandidate, DuplicateStatus
from app.models.fdr import FDRInstrument, FDRStatus, VerificationStatus
from app.models.lifecycle import ReleaseRequest, ReleaseStatus, RenewalRequest
from app.models.user import User, UserRole

router = APIRouter(tags=["Reports & Audit"])


# ─── Report Schemas ─────────────────────────────────────────────────────────

class OverviewReport(BaseModel):
    total_fdrs: int
    status_distribution: Dict[str, int]
    verification_distribution: Dict[str, int]
    total_deposit_value: float
    average_priority_score: float
    pending_duplicates: int
    pending_releases: int
    pending_renewals: int


class MaturityReport(BaseModel):
    maturing_7_days: int
    maturing_15_days: int
    maturing_30_days: int
    already_matured: int
    fdrs: List[Dict[str, Any]]


class AuditEventResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    role: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[UUID] = None
    timestamp: datetime
    before_values: Optional[Dict[str, Any]] = None
    after_values: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    correlation_id: Optional[UUID] = None
    model_config = ConfigDict(from_attributes=True)


# ─── Reports ─────────────────────────────────────────────────────────────────

@router.get("/reports/overview", response_model=OverviewReport)
async def get_overview_report(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.REVIEWER, UserRole.APPROVING_AUTHORITY)),
    db: AsyncSession = Depends(get_db),
) -> OverviewReport:
    """Generate an overview compliance report."""
    # Total FDRs
    total = (await db.execute(select(func.count(FDRInstrument.id)))).scalar() or 0

    # Status distribution
    status_stmt = select(FDRInstrument.status, func.count(FDRInstrument.id)).group_by(FDRInstrument.status)
    status_rows = (await db.execute(status_stmt)).all()
    status_dist = {row[0].value: row[1] for row in status_rows}

    # Verification distribution
    verif_stmt = select(FDRInstrument.verification_status, func.count(FDRInstrument.id)).group_by(FDRInstrument.verification_status)
    verif_rows = (await db.execute(verif_stmt)).all()
    verif_dist = {row[0].value: row[1] for row in verif_rows}

    # Total deposit value
    total_value = (await db.execute(select(func.sum(FDRInstrument.deposit_amount)))).scalar() or 0

    # Average priority
    avg_priority = (await db.execute(select(func.avg(FDRInstrument.review_priority_score)))).scalar() or 0

    # Pending duplicates
    dup_count = (await db.execute(
        select(func.count(DuplicateCandidate.id)).where(DuplicateCandidate.status == DuplicateStatus.PENDING)
    )).scalar() or 0

    # Pending releases
    rel_count = (await db.execute(
        select(func.count(ReleaseRequest.id)).where(ReleaseRequest.status == ReleaseStatus.PENDING)
    )).scalar() or 0

    # Pending renewals
    from app.models.lifecycle import RenewalStatus
    ren_count = (await db.execute(
        select(func.count(RenewalRequest.id)).where(RenewalRequest.status == RenewalStatus.PENDING)
    )).scalar() or 0

    return OverviewReport(
        total_fdrs=total,
        status_distribution=status_dist,
        verification_distribution=verif_dist,
        total_deposit_value=float(total_value),
        average_priority_score=float(avg_priority),
        pending_duplicates=dup_count,
        pending_releases=rel_count,
        pending_renewals=ren_count,
    )


@router.get("/reports/maturity", response_model=MaturityReport)
async def get_maturity_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MaturityReport:
    """Report on FDR maturity timelines."""
    today = date.today()
    institution_id = None
    if current_user.role == UserRole.INSTITUTION_USER:
        institution = await get_current_institution(user=current_user, db=db)
        if not institution:
            raise ForbiddenException("User is not mapped to any valid institution")
        institution_id = institution.id

    async def count_maturing(days: int) -> int:
        stmt = select(func.count(FDRInstrument.id)).where(
            and_(
                FDRInstrument.maturity_date <= today + timedelta(days=days),
                FDRInstrument.maturity_date >= today,
                FDRInstrument.status.notin_([FDRStatus.RELEASED, FDRStatus.REJECTED]),
            )
        )
        if institution_id:
            stmt = stmt.where(FDRInstrument.institution_id == institution_id)
        return (await db.execute(stmt)).scalar() or 0

    matured_stmt = select(func.count(FDRInstrument.id)).where(
            and_(
                FDRInstrument.maturity_date < today,
                FDRInstrument.status.notin_([FDRStatus.RELEASED, FDRStatus.REJECTED]),
            )
        )
    if institution_id:
        matured_stmt = matured_stmt.where(FDRInstrument.institution_id == institution_id)
    matured_count = (await db.execute(matured_stmt)).scalar() or 0

    # Get detailed list (next 60 days)
    detail_stmt = (
        select(FDRInstrument)
        .options(selectinload(FDRInstrument.institution))
        .where(
            and_(
                FDRInstrument.maturity_date <= today + timedelta(days=60),
                FDRInstrument.status.notin_([FDRStatus.RELEASED, FDRStatus.REJECTED]),
            ),
            *([FDRInstrument.institution_id == institution_id] if institution_id else []),
        )
        .order_by(FDRInstrument.maturity_date)
    )
    fdrs = (await db.execute(detail_stmt)).scalars().all()

    fdr_list = []
    for f in fdrs:
        days_until = (f.maturity_date - today).days
        fdr_list.append({
            "id": str(f.id),
            "reference": f.internal_reference,
            "institution": f.institution.name if f.institution else "N/A",
            "bank": f.bank_name,
            "amount": float(f.deposit_amount),
            "maturity_date": str(f.maturity_date),
            "days_until": days_until,
            "status": f.status.value,
        })

    return MaturityReport(
        maturing_7_days=await count_maturing(7),
        maturing_15_days=await count_maturing(15),
        maturing_30_days=await count_maturing(30),
        already_matured=matured_count,
        fdrs=fdr_list,
    )


@router.get("/reports/duplicates")
async def get_duplicates_report(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.REVIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Report on all duplicate candidates."""
    stmt = (
        select(DuplicateCandidate)
        .order_by(desc(DuplicateCandidate.created_at))
    )
    candidates = (await db.execute(stmt)).scalars().all()

    return [{
        "id": str(c.id),
        "fdr_a_id": str(c.fdr_instrument_a_id),
        "fdr_b_id": str(c.fdr_instrument_b_id),
        "match_score": c.match_score,
        "match_reasons": c.match_reasons,
        "matching_fields": c.matching_fields,
        "differing_fields": c.differing_fields,
        "file_hash_match": c.file_hash_match,
        "status": c.status.value,
        "review_notes": c.review_notes,
        "created_at": str(c.created_at),
    } for c in candidates]


@router.get("/reports/pending-cases")
async def get_pending_cases_report(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.REVIEWER, UserRole.APPROVING_AUTHORITY)),
    db: AsyncSession = Depends(get_db),
):
    """Report on all pending review cases."""
    stmt = (
        select(FDRInstrument)
        .options(selectinload(FDRInstrument.institution))
        .where(
            FDRInstrument.status.in_([
                FDRStatus.SUBMITTED, FDRStatus.UNDER_REVIEW, FDRStatus.VALIDATED,
                FDRStatus.CORRECTION_REQUESTED
            ])
        )
        .order_by(desc(FDRInstrument.review_priority_score))
    )
    fdrs = (await db.execute(stmt)).scalars().all()

    return [{
        "id": str(f.id),
        "reference": f.internal_reference,
        "institution": f.institution.name if f.institution else "N/A",
        "bank": f.bank_name,
        "amount": float(f.deposit_amount),
        "status": f.status.value,
        "priority_score": f.review_priority_score,
        "priority_reasons": f.review_priority_reasons,
        "created_at": str(f.created_at),
        "updated_at": str(f.updated_at),
    } for f in fdrs]


@router.get("/reports/export")
async def export_fdrs_csv(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.REVIEWER, UserRole.APPROVING_AUTHORITY)),
    db: AsyncSession = Depends(get_db),
):
    """Export all FDR records as CSV."""
    stmt = (
        select(FDRInstrument)
        .options(selectinload(FDRInstrument.institution))
        .order_by(FDRInstrument.created_at)
    )
    fdrs = (await db.execute(stmt)).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Internal Reference", "Institution", "Bank", "Branch", "FDR Number",
        "Amount", "Currency", "Issue Date", "Maturity Date", "Status",
        "Verification Status", "Priority Score", "Duplicate Flag",
        "Created At", "Updated At"
    ])
    for f in fdrs:
        writer.writerow([
            f.internal_reference,
            f.institution.name if f.institution else "",
            f.bank_name,
            f.branch_name or "",
            f.fdr_number,
            str(f.deposit_amount),
            f.currency,
            str(f.issue_date),
            str(f.maturity_date),
            f.status.value,
            f.verification_status.value,
            f.review_priority_score,
            f.has_potential_duplicate,
            str(f.created_at),
            str(f.updated_at),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=fdr_export_{date.today()}.csv"},
    )


# ─── Audit Trail ─────────────────────────────────────────────────────────────

@router.get("/audit", response_model=List[AuditEventResponse])
async def list_audit_events(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[UUID] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.REVIEWER, UserRole.APPROVING_AUTHORITY)),
    db: AsyncSession = Depends(get_db),
) -> List[AuditEventResponse]:
    """List audit events with optional filters."""
    conditions = []
    if entity_type:
        conditions.append(AuditEvent.entity_type == entity_type)
    if entity_id:
        conditions.append(AuditEvent.entity_id == entity_id)
    if action:
        conditions.append(AuditEvent.action.ilike(f"%{action}%"))
    if user_id:
        conditions.append(AuditEvent.user_id == user_id)

    stmt = (
        select(AuditEvent)
        .where(*conditions) if conditions else select(AuditEvent)
    )
    stmt = stmt.order_by(desc(AuditEvent.timestamp)).offset(offset).limit(limit)

    result = await db.execute(stmt)
    events = result.scalars().all()
    return [AuditEventResponse.model_validate(e) for e in events]


@router.get("/audit/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    event_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> AuditEventResponse:
    """Get a specific audit event."""
    from app.core.exceptions import NotFoundException
    stmt = select(AuditEvent).where(AuditEvent.id == event_id)
    event = (await db.execute(stmt)).scalars().first()
    if not event:
        raise NotFoundException("Audit event not found")
    return AuditEventResponse.model_validate(event)
