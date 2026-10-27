"""Notification endpoints for in-app notification center."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import ForbiddenException, NotFoundException
from app.database import get_db
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.schemas.common import SuccessResponse

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    message: str
    notification_type: NotificationType
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    is_read: bool
    due_date: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(False, description="Show only unread notifications"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[NotificationResponse]:
    """List notifications for the current user."""
    conditions = [Notification.user_id == current_user.id]
    if unread_only:
        conditions.append(Notification.is_read == False)

    stmt = (
        select(Notification)
        .where(*conditions)
        .order_by(desc(Notification.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    notifications = result.scalars().all()
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.post("/{notification_id}/read", response_model=SuccessResponse)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """Mark a notification as read."""
    stmt = select(Notification).where(Notification.id == notification_id)
    notif = (await db.execute(stmt)).scalars().first()
    if not notif:
        raise NotFoundException("Notification not found")
    if notif.user_id != current_user.id:
        raise ForbiddenException("Cannot mark another user's notification")

    notif.is_read = True
    await db.commit()
    return SuccessResponse(message="Notification marked as read")


@router.post("/read-all", response_model=SuccessResponse)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """Mark all notifications as read for the current user."""
    stmt = (
        update(Notification)
        .where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False,
            )
        )
        .values(is_read=True)
    )
    await db.execute(stmt)
    await db.commit()
    return SuccessResponse(message="All notifications marked as read")
