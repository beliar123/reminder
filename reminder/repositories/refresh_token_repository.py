from datetime import datetime, timezone

from sqlalchemy import select

from reminder.models.refresh_token import RefreshToken
from reminder.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def create(self, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:  # type: ignore[override]
        return await super().create(user_id=user_id, token_hash=token_hash, expires_at=expires_at)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> RefreshToken:
        return await self.update(token, revoked_at=datetime.now(tz=timezone.utc))
