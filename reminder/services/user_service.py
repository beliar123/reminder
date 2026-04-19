from dataclasses import dataclass

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from reminder.models.user import User
from reminder.repositories.user_repository import UserRepository

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserNotFoundError(Exception):
    pass


class EmailAlreadyExistsError(Exception):
    pass


@dataclass
class UpdateUserData:
    name: str | None = None
    email: str | None = None
    timezone: str | None = None
    password: str | None = None


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)

    async def create_user(self, email: str, password: str, name: str | None = None, timezone: str | None = None) -> User:
        existing = await self._repo.get_by_email(email)
        if existing is not None:
            raise EmailAlreadyExistsError(email)
        hashed = _pwd_context.hash(password)
        kwargs: dict = {"email": email, "password": hashed}
        if name is not None:
            kwargs["name"] = name
        if timezone is not None:
            kwargs["timezone"] = timezone
        return await self._repo.create(**kwargs)

    async def get_by_id(self, user_id: int) -> User:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    async def update_user(self, user_id: int, data: UpdateUserData) -> User:
        user = await self.get_by_id(user_id)
        updates: dict = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.email is not None:
            existing = await self._repo.get_by_email(data.email)
            if existing is not None and existing.id != user_id:
                raise EmailAlreadyExistsError(data.email)
            updates["email"] = data.email
        if data.timezone is not None:
            updates["timezone"] = data.timezone
        if data.password is not None:
            updates["password"] = _pwd_context.hash(data.password)
        if not updates:
            return user
        return await self._repo.update(user, **updates)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return _pwd_context.verify(plain, hashed)
