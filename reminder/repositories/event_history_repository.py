from datetime import datetime

from sqlalchemy import select

from reminder.models.event_history import EventHistory
from reminder.repositories.base import BaseRepository


class EventHistoryRepository(BaseRepository[EventHistory]):
    model = EventHistory

    async def create(  # type: ignore[override]
        self,
        event_id: int,
        scheduled_at: datetime,
        reminded_at: datetime,
    ) -> EventHistory:
        return await super().create(
            event_id=event_id,
            scheduled_at=scheduled_at,
            reminded_at=reminded_at,
        )

    async def list_by_event(self, event_id: int) -> list[EventHistory]:
        result = await self.session.execute(
            select(EventHistory)
            .where(EventHistory.event_id == event_id)
            .order_by(EventHistory.scheduled_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_event_paginated(
        self, event_id: int, cursor: int | None = None, limit: int = 20
    ) -> list[EventHistory]:
        q = select(EventHistory).where(EventHistory.event_id == event_id)
        if cursor is not None:
            q = q.where(EventHistory.id < cursor)
        q = q.order_by(EventHistory.id.desc()).limit(limit)
        result = await self.session.execute(q)
        return list(result.scalars().all())
