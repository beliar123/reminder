import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from reminder.models.user import User
from reminder.repositories.refresh_token_repository import RefreshTokenRepository
from reminder.repositories.user_repository import UserRepository
from reminder.services.user_service import EmailAlreadyExistsError, UserService

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)


class InvalidCredentialsError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


class AuthService:
    def __init__(self, session: AsyncSession, secret_key: str) -> None:
        self._user_service = UserService(session)
        self._user_repo = UserRepository(session)
        self._token_repo = RefreshTokenRepository(session)
        self._secret = secret_key

    def _issue_access_token(self, user_id: int) -> str:
        now = datetime.now(tz=timezone.utc)
        payload = {"sub": str(user_id), "iat": now, "exp": now + ACCESS_TOKEN_TTL}
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    async def _issue_refresh_token(self, user_id: int) -> str:
        raw = secrets.token_urlsafe(64)
        expires_at = datetime.now(tz=timezone.utc) + REFRESH_TOKEN_TTL
        await self._token_repo.create(
            user_id=user_id,
            token_hash=self._hash_token(raw),
            expires_at=expires_at,
        )
        return raw

    async def register(self, email: str, password: str, name: str | None = None, timezone: str | None = None) -> tuple[User, TokenPair]:
        user = await self._user_service.create_user(email, password, name=name, timezone=timezone)
        tokens = TokenPair(
            access_token=self._issue_access_token(user.id),
            refresh_token=await self._issue_refresh_token(user.id),
        )
        return user, tokens

    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        user = await self._user_repo.get_by_email(email)
        if user is None or not self._user_service.verify_password(password, user.password):
            raise InvalidCredentialsError
        tokens = TokenPair(
            access_token=self._issue_access_token(user.id),
            refresh_token=await self._issue_refresh_token(user.id),
        )
        return user, tokens

    async def refresh_access_token(self, raw_refresh_token: str) -> str:
        token = await self._token_repo.get_by_hash(self._hash_token(raw_refresh_token))
        now = datetime.now(tz=timezone.utc)
        if token is None or token.revoked_at is not None or token.expires_at <= now:
            raise InvalidTokenError
        return self._issue_access_token(token.user_id)

    async def logout(self, raw_refresh_token: str) -> None:
        token = await self._token_repo.get_by_hash(self._hash_token(raw_refresh_token))
        if token is None or token.revoked_at is not None:
            raise InvalidTokenError
        await self._token_repo.revoke(token)

    def decode_access_token(self, token: str) -> int:
        try:
            payload = jwt.decode(token, self._secret, algorithms=["HS256"])
            return int(payload["sub"])
        except jwt.PyJWTError:
            raise InvalidTokenError
