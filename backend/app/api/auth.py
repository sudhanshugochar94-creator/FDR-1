from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_institution, get_current_user
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.database import get_db
from app.models.institution import Institution
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.schemas.common import SuccessResponse
from app.schemas.institution import InstitutionBriefResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    stmt = select(User).where(User.email == credentials.email.strip().lower())
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")

    if not user.is_active:
        raise ForbiddenException("Account is deactivated")

    # Fetch primary institution if any
    institution_obj = await get_current_institution(user=user, db=db)
    institution_brief = (
        InstitutionBriefResponse(
            id=institution_obj.id,
            name=institution_obj.name,
            code=institution_obj.code,
        )
        if institution_obj
        else None
    )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    user_response = UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        institution=institution_brief,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        user=user_response,
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout(current_user: User = Depends(get_current_user)) -> SuccessResponse:
    return SuccessResponse(message=f"User {current_user.email} successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    institution_obj = await get_current_institution(user=current_user, db=db)
    institution_brief = (
        InstitutionBriefResponse(
            id=institution_obj.id,
            name=institution_obj.name,
            code=institution_obj.code,
        )
        if institution_obj
        else None
    )

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        institution=institution_brief,
    )
