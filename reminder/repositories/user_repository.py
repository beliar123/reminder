from sqlalchemy import select

from reminder.models.user import User
from reminder.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, email: str, password: str) -> User:  # type: ignore[override]
        return await super().create(email=email, password=password)
