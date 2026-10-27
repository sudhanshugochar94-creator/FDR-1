from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user, require_role
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.database import get_db
from app.models.institution import Institution
from app.models.user import User, UserRole
from app.models.user_institution_role import UserInstitutionRole
from app.schemas.institution import InstitutionCreate, InstitutionResponse

router = APIRouter(prefix="/institutions", tags=["Institutions"])


@router.get("", response_model=List[InstitutionResponse])
async def list_institutions(
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN,
            UserRole.REVIEWER,
            UserRole.APPROVING_AUTHORITY,
        )
    ),
    db: AsyncSession = Depends(get_db),
) -> List[InstitutionResponse]:
    stmt = select(Institution).order_by(Institution.name.asc())
    result = await db.execute(stmt)
    institutions = result.scalars().all()
    return list(institutions)


@router.get("/{institution_id}", response_model=InstitutionResponse)
async def get_institution(
    institution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InstitutionResponse:
    # If user is institution_user, ensure they belong to this institution
    if current_user.role == UserRole.INSTITUTION_USER:
        role_stmt = select(UserInstitutionRole).where(
            UserInstitutionRole.user_id == current_user.id,
            UserInstitutionRole.institution_id == institution_id,
        )
        user_role = (await db.execute(role_stmt)).scalars().first()
        if not user_role:
            raise ForbiddenException("You do not have access to view this institution")

    stmt = select(Institution).where(Institution.id == institution_id)
    result = await db.execute(stmt)
    institution = result.scalars().first()

    if not institution:
        raise NotFoundException(f"Institution with id '{institution_id}' not found")

    return institution


@router.post("", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED)
async def create_institution(
    payload: InstitutionCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> InstitutionResponse:
    stmt = select(Institution).where(Institution.code == payload.code.strip().upper())
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        raise ConflictException(f"Institution with code '{payload.code}' already exists")

    institution = Institution(
        name=payload.name.strip(),
        code=payload.code.strip().upper(),
        address=payload.address,
        city=payload.city,
        state=payload.state,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        is_active=payload.is_active,
    )
    db.add(institution)
    await db.commit()
    await db.refresh(institution)
    return institution
