from datetime import datetime

from sqlalchemy import select

from reminder.enums import Category
from reminder.models.event import Event
from reminder.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    model = Event

    async def get_by_id_and_user(self, event_id: int, user_id: int) -> Event | None:
        result = await self.session.execute(
            select(Event).where(Event.id == event_id, Event.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int, category: Category | None = None) -> list[Event]:
        query = select(Event).where(Event.user_id == user_id)
        if category is not None:
            query = query.where(Event.category == category)
        result = await self.session.execute(query.order_by(Event.next_remind_at.asc().nulls_last()))
        return list(result.scalars().all())

    async def get_due(self, now: datetime) -> list[Event]:
        result = await self.session.execute(
            select(Event).where(
                Event.next_remind_at <= now,
                Event.is_completed.is_(False),
            )
        )
        return list(result.scalars().all())
