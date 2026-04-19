from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from reminder.enums import CATEGORIES_YEARLY_ONLY, Category, Recurrence
from reminder.models.event import Event
from reminder.repositories.event_repository import EventRepository


@dataclass
class CreateEventData:
    title: str
    category: Category
    recurrence: Recurrence
    next_remind_at: datetime
    description: str | None = None


@dataclass
class UpdateEventData:
    title: str | None = None
    description: str | None = None
    category: Category | None = None
    recurrence: Recurrence | None = None
    next_remind_at: datetime | None = None


class EventNotFoundError(Exception):
    pass


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = EventRepository(session)

    def _enforce_yearly(self, category: Category, recurrence: Recurrence) -> Recurrence:
        if category in CATEGORIES_YEARLY_ONLY:
            return Recurrence.yearly
        return recurrence

    async def create_event(self, user_id: int, data: CreateEventData) -> Event:
        recurrence = self._enforce_yearly(data.category, data.recurrence)
        return await self._repo.create(
            user_id=user_id,
            title=data.title,
            description=data.description,
            category=data.category,
            recurrence=recurrence,
            next_remind_at=data.next_remind_at,
        )

    async def get_event(self, user_id: int, event_id: int) -> Event:
        event = await self._repo.get_by_id_and_user(event_id, user_id)
        if event is None:
            raise EventNotFoundError(event_id)
        return event

    async def list_events(self, user_id: int, category: Category | None = None) -> list[Event]:
        return await self._repo.list_by_user(user_id, category)

    async def update_event(self, user_id: int, event_id: int, data: UpdateEventData) -> Event:
        event = await self.get_event(user_id, event_id)

        updates: dict = {}
        if data.title is not None:
            updates["title"] = data.title
        if data.description is not None:
            updates["description"] = data.description
        if data.next_remind_at is not None:
            updates["next_remind_at"] = data.next_remind_at

        new_category = data.category if data.category is not None else event.category
        new_recurrence = data.recurrence if data.recurrence is not None else event.recurrence

        updates["category"] = new_category
        updates["recurrence"] = self._enforce_yearly(new_category, new_recurrence)

        return await self._repo.update(event, **updates)

    async def delete_event(self, user_id: int, event_id: int) -> None:
        event = await self.get_event(user_id, event_id)
        await self._repo.delete(event)
