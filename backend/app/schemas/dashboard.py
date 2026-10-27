from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class StatusCount(BaseModel):
    status: str
    count: int
    label: str


class RecentActivity(BaseModel):
    id: UUID
    title: str
    action: str
    entity_type: str
    entity_id: Optional[UUID] = None
    timestamp: datetime
    user_name: Optional[str] = None
    details: Optional[Any] = None

    model_config = ConfigDict(from_attributes=True)


class UpcomingDeadline(BaseModel):
    id: UUID
    internal_reference: str
    fdr_number: str
    bank_name: str
    deposit_amount: Decimal
    currency: str
    maturity_date: date
    days_remaining: int
    institution_id: UUID
    institution_name: str

    model_config = ConfigDict(from_attributes=True)


class MonthlyMaturity(BaseModel):
    month: str
    count: int
    total_amount: Decimal


class DashboardResponse(BaseModel):
    total_fdrs: int
    active_fdrs: int
    awaiting_verification: int
    potential_duplicates: int
    needs_review: int
    maturing_30_days: int
    overdue_actions: int
    renewal_requests: int
    pending_releases: int
    released_fdrs: int
    status_distribution: List[StatusCount]
    monthly_maturities: List[MonthlyMaturity]
    recent_updates: List[RecentActivity]
    upcoming_deadlines: List[UpcomingDeadline]

    model_config = ConfigDict(from_attributes=True)
