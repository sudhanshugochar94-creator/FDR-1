from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.deps import get_current_institution, get_current_user
from app.core.exceptions import ForbiddenException
from app.database import get_db
from app.models.audit import AuditEvent
from app.models.document import FDRDocument
from app.models.fdr import FDRInstrument, FDRStatus, VerificationStatus
from app.models.institution import Institution
from app.models.lifecycle import ReleaseRequest, ReleaseStatus, RenewalRequest, RenewalStatus
from app.models.user import User, UserRole
from app.schemas.dashboard import (
    DashboardResponse,
    MonthlyMaturity,
    RecentActivity,
    StatusCount,
    UpcomingDeadline,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    institution_id: Optional[UUID] = Query(None, description="Optional institution filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    today = date.today()
    in_30_days = today + timedelta(days=30)

    # Determine institution filter scope
    filter_inst_id: Optional[UUID] = None
    if current_user.role == UserRole.INSTITUTION_USER:
        inst = await get_current_institution(user=current_user, db=db)
        if not inst:
            raise ForbiddenException("User is not mapped to any valid institution")
        filter_inst_id = inst.id
    elif institution_id:
        filter_inst_id = institution_id

    # Base conditions for FDR
    fdr_base_cond = []
    if filter_inst_id:
        fdr_base_cond.append(FDRInstrument.institution_id == filter_inst_id)

    # 1. Total FDRs
    stmt_total = select(func.count(FDRInstrument.id)).where(*fdr_base_cond)
    total_fdrs = (await db.execute(stmt_total)).scalar() or 0

    # 2. Active FDRs
    stmt_active = select(func.count(FDRInstrument.id)).where(
        *fdr_base_cond,
        FDRInstrument.status == FDRStatus.ACTIVE,
    )
    active_fdrs = (await db.execute(stmt_active)).scalar() or 0

    # 3. Awaiting verification
    stmt_awaiting = select(func.count(FDRInstrument.id)).where(
        *fdr_base_cond,
        or_(
            FDRInstrument.verification_status.in_([
                VerificationStatus.PENDING,
                VerificationStatus.AWAITING_BANK_VERIFICATION,
            ]),
            FDRInstrument.status.in_([
                FDRStatus.SUBMITTED,
                FDRStatus.EXTRACTED,
                FDRStatus.VALIDATED,
                FDRStatus.UNDER_REVIEW,
            ]),
        ),
    )
    awaiting_verification = (await db.execute(stmt_awaiting)).scalar() or 0

    # 4. Potential Duplicates
    stmt_dup = select(func.count(FDRInstrument.id)).where(
        *fdr_base_cond,
        FDRInstrument.has_potential_duplicate.is_(True),
    )
    potential_duplicates = (await db.execute(stmt_dup)).scalar() or 0

    # 5. Needs Review
    stmt_review = select(func.count(FDRInstrument.id)).where(
        *fdr_base_cond,
        FDRInstrument.status.in_([FDRStatus.UNDER_REVIEW, FDRStatus.VALIDATED]),
    )
    needs_review = (await db.execute(stmt_review)).scalar() or 0

    # 6. Maturing in 30 days
    stmt_maturing = select(func.count(FDRInstrument.id)).where(
        *fdr_base_cond,
        FDRInstrument.status == FDRStatus.ACTIVE,
        FDRInstrument.maturity_date >= today,
        FDRInstrument.maturity_date <= in_30_days,
    )
    maturing_30_days = (await db.execute(stmt_maturing)).scalar() or 0

    # 7. Overdue actions (matured but still active/pending or correction requested)
    stmt_overdue = select(func.count(FDRInstrument.id)).where(
        *fdr_base_cond,
        or_(
            and_(
                FDRInstrument.maturity_date < today,
                FDRInstrument.status.in_([FDRStatus.ACTIVE, FDRStatus.RENEWAL_PENDING]),
            ),
            FDRInstrument.status == FDRStatus.CORRECTION_REQUESTED,
        ),
    )
    overdue_actions = (await db.execute(stmt_overdue)).scalar() or 0

    # 8. Renewal requests
    stmt_renewal = select(func.count(RenewalRequest.id)).join(
        FDRInstrument,
        RenewalRequest.original_fdr_id == FDRInstrument.id,
    ).where(RenewalRequest.status == RenewalStatus.PENDING)
    if filter_inst_id:
        stmt_renewal = stmt_renewal.where(FDRInstrument.institution_id == filter_inst_id)
    renewal_requests = (await db.execute(stmt_renewal)).scalar() or 0

    # 9. Pending releases
    stmt_release = select(func.count(ReleaseRequest.id)).join(
        FDRInstrument,
        ReleaseRequest.fdr_instrument_id == FDRInstrument.id,
    ).where(
        ReleaseRequest.status.in_([ReleaseStatus.PENDING, ReleaseStatus.UNDER_REVIEW])
    )
    if filter_inst_id:
        stmt_release = stmt_release.where(FDRInstrument.institution_id == filter_inst_id)
    pending_releases = (await db.execute(stmt_release)).scalar() or 0

    # 10. Released FDRs
    stmt_released = select(func.count(FDRInstrument.id)).where(
        *fdr_base_cond,
        FDRInstrument.status == FDRStatus.RELEASED,
    )
    released_fdrs = (await db.execute(stmt_released)).scalar() or 0

    # Status distribution
    stmt_dist = (
        select(FDRInstrument.status, func.count(FDRInstrument.id))
        .where(*fdr_base_cond)
        .group_by(FDRInstrument.status)
    )
    dist_rows = (await db.execute(stmt_dist)).all()
    dist_dict = {status.value if hasattr(status, "value") else str(status): count for status, count in dist_rows}

    status_distribution = [
        StatusCount(
            status=s.value,
            count=dist_dict.get(s.value, 0),
            label=s.value.replace("_", " ").title(),
        )
        for s in FDRStatus
    ]

    # Include every month in the forecast so zero-maturity months still appear.
    first_month = date(today.year, today.month, 1)
    forecast_months = []
    for offset in range(6):
        month_index = first_month.month - 1 + offset
        year = first_month.year + month_index // 12
        month = month_index % 12 + 1
        forecast_months.append(date(year, month, 1))

    forecast_end_index = first_month.month - 1 + 6
    forecast_end = date(
        first_month.year + forecast_end_index // 12,
        forecast_end_index % 12 + 1,
        1,
    )
    maturity_stmt = select(
        FDRInstrument.maturity_date,
        FDRInstrument.deposit_amount,
    ).where(
        FDRInstrument.maturity_date >= today,
        FDRInstrument.maturity_date < forecast_end,
        FDRInstrument.status.notin_([FDRStatus.RELEASED, FDRStatus.REJECTED]),
        *fdr_base_cond,
    )
    maturity_rows = (await db.execute(maturity_stmt)).all()
    maturities_by_month = {
        month: {"count": 0, "total_amount": Decimal("0.00")}
        for month in forecast_months
    }
    for maturity_date, deposit_amount in maturity_rows:
        month = date(maturity_date.year, maturity_date.month, 1)
        monthly_total = maturities_by_month[month]
        monthly_total["count"] += 1
        monthly_total["total_amount"] += deposit_amount

    monthly_maturities = [
        MonthlyMaturity(
            month=month.strftime("%b %Y"),
            count=maturities_by_month[month]["count"],
            total_amount=maturities_by_month[month]["total_amount"],
        )
        for month in forecast_months
    ]

    # Recent updates from AuditEvent
    stmt_audit = (
        select(AuditEvent)
        .options(selectinload(AuditEvent.user))
    )
    if filter_inst_id:
        institution_fdr_ids = select(FDRInstrument.id).where(
            FDRInstrument.institution_id == filter_inst_id
        )
        institution_document_ids = select(FDRDocument.id).where(
            FDRDocument.fdr_instrument_id.in_(institution_fdr_ids)
        )
        stmt_audit = stmt_audit.where(
            or_(
                and_(
                    AuditEvent.entity_type == "FDRInstrument",
                    AuditEvent.entity_id.in_(institution_fdr_ids),
                ),
                and_(
                    AuditEvent.entity_type == "FDRDocument",
                    AuditEvent.entity_id.in_(institution_document_ids),
                ),
            )
        )
    stmt_audit = stmt_audit.order_by(AuditEvent.timestamp.desc()).limit(10)
    audit_events = (await db.execute(stmt_audit)).scalars().all()
    recent_updates: List[RecentActivity] = []
    for event in audit_events:
        user_name = event.user.full_name if event.user else "System"
        recent_updates.append(
            RecentActivity(
                id=event.id,
                title=f"{event.action.replace('_', ' ').title()} - {event.entity_type}",
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                timestamp=event.timestamp,
                user_name=user_name,
                details=event.after_values or event.before_values,
            )
        )

    # Upcoming deadlines
    stmt_upcoming = (
        select(FDRInstrument)
        .options(selectinload(FDRInstrument.institution))
        .where(
            *fdr_base_cond,
            FDRInstrument.status.in_([FDRStatus.ACTIVE, FDRStatus.RENEWAL_PENDING]),
            FDRInstrument.maturity_date >= today,
        )
        .order_by(FDRInstrument.maturity_date.asc())
        .limit(5)
    )
    upcoming_fdrs = (await db.execute(stmt_upcoming)).scalars().all()
    upcoming_deadlines: List[UpcomingDeadline] = []
    for f in upcoming_fdrs:
        days_remaining = (f.maturity_date - today).days
        inst_name = f.institution.name if f.institution else "Unknown Institution"
        upcoming_deadlines.append(
            UpcomingDeadline(
                id=f.id,
                internal_reference=f.internal_reference,
                fdr_number=f.fdr_number,
                bank_name=f.bank_name,
                deposit_amount=f.deposit_amount,
                currency=f.currency,
                maturity_date=f.maturity_date,
                days_remaining=days_remaining,
                institution_id=f.institution_id,
                institution_name=inst_name,
            )
        )

    return DashboardResponse(
        total_fdrs=total_fdrs,
        active_fdrs=active_fdrs,
        awaiting_verification=awaiting_verification,
        potential_duplicates=potential_duplicates,
        needs_review=needs_review,
        maturing_30_days=maturing_30_days,
        overdue_actions=overdue_actions,
        renewal_requests=renewal_requests,
        pending_releases=pending_releases,
        released_fdrs=released_fdrs,
        status_distribution=status_distribution,
        monthly_maturities=monthly_maturities,
        recent_updates=recent_updates,
        upcoming_deadlines=upcoming_deadlines,
    )
