import uuid
from typing import Callable, Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
try:
    from jose import JWTError
except ImportError:
    from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.database import get_db
from app.models.institution import Institution
from app.models.fdr import FDRInstrument
from app.models.user import User, UserRole
from app.models.user_institution_role import UserInstitutionRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise UnauthorizedException("Authentication token is required")

    try:
        payload = decode_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedException("Token missing subject identifier")
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise UnauthorizedException("Could not validate authentication credentials")

    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.institution_roles))
    )
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise UnauthorizedException("User not found")
    if not user.is_active:
        raise ForbiddenException("User account is inactive")

    return user


def require_role(*roles: UserRole) -> Callable:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            required = [r.value for r in roles]
            raise ForbiddenException(
                f"User does not have required permissions. Required role in: {required}"
            )
        return current_user

    return role_checker


async def get_current_institution(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[Institution]:
    stmt = (
        select(Institution)
        .join(UserInstitutionRole, UserInstitutionRole.institution_id == Institution.id)
        .where(UserInstitutionRole.user_id == user.id)
        .order_by(UserInstitutionRole.is_primary.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def ensure_fdr_institution_access(
    fdr: FDRInstrument,
    user: User,
    db: AsyncSession,
) -> None:
    if user.role != UserRole.INSTITUTION_USER:
        return

    institution = await get_current_institution(user=user, db=db)
    if not institution or fdr.institution_id != institution.id:
        raise ForbiddenException("You do not have permission to access this FDR")
