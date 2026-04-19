from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from reminder.enums import CATEGORIES_WITH_HISTORY, Recurrence
from reminder.models.event_history import EventHistory
from reminder.repositories.event_history_repository import EventHistoryRepository
from reminder.repositories.event_repository import EventRepository
from reminder.utils.recurrence import next_remind_date


class EventNotFoundError(Exception):
    pass


class HistoryNotFoundError(Exception):
    pass


class EventHistoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._event_repo = EventRepository(session)
        self._history_repo = EventHistoryRepository(session)

    async def advance_reminder(self, event_id: int) -> EventHistory | None:
        """Called when next_remind_at fires.

        - Creates EventHistory for non-Birthday categories.
        - Advances next_remind_at for recurring events.
        - Marks one_time events as completed.

        Returns the created EventHistory record (or None for Birthday).
        """
        event = await self._event_repo.get_by_id(event_id)
        if event is None:
            raise EventNotFoundError(event_id)

        scheduled_at = event.next_remind_at
        now = datetime.now(tz=timezone.utc)

        history: EventHistory | None = None
        if event.category in CATEGORIES_WITH_HISTORY:
            history = await self._history_repo.create(
                event_id=event_id,
                scheduled_at=scheduled_at,
                reminded_at=now,
            )

        if event.recurrence == Recurrence.one_time:
            await self._event_repo.update(event, next_remind_at=None, is_completed=True)
        else:
            new_date = next_remind_date(scheduled_at, event.recurrence)
            await self._event_repo.update(event, next_remind_at=new_date)

        return history

    async def mark_completed(
        self,
        user_id: int,
        history_id: int,
        notes: str | None = None,
    ) -> EventHistory:
        """Mark a history record as completed, verifying ownership via user_id."""
        history = await self._history_repo.get_by_id(history_id)
        if history is None:
            raise HistoryNotFoundError(history_id)

        event = await self._event_repo.get_by_id_and_user(history.event_id, user_id)
        if event is None:
            raise HistoryNotFoundError(history_id)

        return await self._history_repo.update(
            history,
            completed_at=datetime.now(tz=timezone.utc),
            notes=notes,
        )

    async def list_history(self, user_id: int, event_id: int) -> list[EventHistory]:
        """Return history records for an event, verifying ownership."""
        event = await self._event_repo.get_by_id_and_user(event_id, user_id)
        if event is None:
            raise EventNotFoundError(event_id)
        return await self._history_repo.list_by_event(event_id)
