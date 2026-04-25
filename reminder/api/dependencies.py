from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from reminder.api.settings import api_settings
from reminder.database import AsyncSessionFactory
from reminder.models.user import User
from reminder.services.auth_service import AuthService, InvalidTokenError
from reminder.services.user_service import UserNotFoundError, UserService

_bearer = HTTPBearer()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        async with session.begin():
            yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    auth_service = AuthService(session, api_settings.secret_key)
    try:
        user_id = auth_service.decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_service = UserService(session)
    try:
        return await user_service.get_by_id(user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
