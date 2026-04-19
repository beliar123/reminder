from datetime import datetime, timezone

import pytest

from reminder.enums import Category, Recurrence
from reminder.repositories.user_repository import UserRepository
from reminder.services.event_service import CreateEventData, EventService
from reminder.services.event_history_service import EventHistoryService, HistoryNotFoundError


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@pytest.fixture
async def user(db_session):
    return await UserRepository(db_session).create(email="hist@example.com", password="hashed")


@pytest.fixture
async def event_service(db_session):
    return EventService(db_session)


@pytest.fixture
async def history_service(db_session):
    return EventHistoryService(db_session)


async def _make_event(event_service, user_id, category=Category.meeting, recurrence=Recurrence.weekly):
    data = CreateEventData(
        title="Test event",
        category=category,
        recurrence=recurrence,
        next_remind_at=_now(),
    )
    return await event_service.create_event(user_id, data)


@pytest.mark.asyncio
async def test_advance_reminder_creates_history_for_meeting(user, event_service, history_service):
    event = await _make_event(event_service, user.id, Category.meeting)
    history = await history_service.advance_reminder(event.id)

    assert history is not None
    assert history.event_id == event.id
    assert history.completed_at is None


@pytest.mark.asyncio
async def test_advance_reminder_creates_history_for_anniversary(user, event_service, history_service):
    event = await _make_event(event_service, user.id, Category.anniversary, Recurrence.yearly)
    history = await history_service.advance_reminder(event.id)
    assert history is not None


@pytest.mark.asyncio
async def test_advance_reminder_creates_history_for_personal(user, event_service, history_service):
    event = await _make_event(event_service, user.id, Category.personal)
    history = await history_service.advance_reminder(event.id)
    assert history is not None


@pytest.mark.asyncio
async def test_advance_reminder_no_history_for_birthday(user, event_service, history_service, db_session):
    event = await _make_event(event_service, user.id, Category.birthday, Recurrence.yearly)
    history = await history_service.advance_reminder(event.id)
    assert history is None

    all_history = await history_service.list_history(user.id, event.id)
    assert len(all_history) == 0


@pytest.mark.asyncio
async def test_advance_reminder_advances_date_for_recurring(user, event_service, history_service, db_session):
    event = await _make_event(event_service, user.id, Category.meeting, Recurrence.weekly)
    original_date = event.next_remind_at
    await history_service.advance_reminder(event.id)

    from reminder.repositories.event_repository import EventRepository
    updated = await EventRepository(db_session).get_by_id(event.id)
    assert updated.next_remind_at > original_date
    assert updated.is_completed is False


@pytest.mark.asyncio
async def test_advance_reminder_marks_one_time_completed(user, event_service, history_service, db_session):
    event = await _make_event(event_service, user.id, Category.meeting, Recurrence.one_time)
    await history_service.advance_reminder(event.id)

    from reminder.repositories.event_repository import EventRepository
    updated = await EventRepository(db_session).get_by_id(event.id)
    assert updated.next_remind_at is None
    assert updated.is_completed is True


@pytest.mark.asyncio
async def test_mark_completed_with_notes(user, event_service, history_service):
    event = await _make_event(event_service, user.id, Category.meeting)
    history = await history_service.advance_reminder(event.id)

    updated = await history_service.mark_completed(user.id, history.id, notes="Done and done")
    assert updated.completed_at is not None
    assert updated.notes == "Done and done"


@pytest.mark.asyncio
async def test_mark_completed_without_notes(user, event_service, history_service):
    event = await _make_event(event_service, user.id, Category.personal)
    history = await history_service.advance_reminder(event.id)

    updated = await history_service.mark_completed(user.id, history.id)
    assert updated.completed_at is not None
    assert updated.notes is None


@pytest.mark.asyncio
async def test_mark_completed_wrong_user_raises(user, event_service, history_service, db_session):
    other = await UserRepository(db_session).create(email="other@hist.com", password="hashed")
    event = await _make_event(event_service, user.id, Category.meeting)
    history = await history_service.advance_reminder(event.id)

    with pytest.raises(HistoryNotFoundError):
        await history_service.mark_completed(other.id, history.id)
