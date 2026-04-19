from datetime import datetime, timezone

import pytest

from reminder.enums import Category, Recurrence
from reminder.repositories.user_repository import UserRepository
from reminder.services.event_service import (
    CreateEventData,
    EventNotFoundError,
    EventService,
    UpdateEventData,
)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@pytest.fixture
async def user(db_session):
    repo = UserRepository(db_session)
    return await repo.create(email="test@example.com", password="hashed")


@pytest.fixture
async def service(db_session):
    return EventService(db_session)


@pytest.mark.asyncio
async def test_create_event(user, service):
    data = CreateEventData(
        title="Team meeting",
        category=Category.meeting,
        recurrence=Recurrence.weekly,
        next_remind_at=_now(),
    )
    event = await service.create_event(user.id, data)

    assert event.id is not None
    assert event.user_id == user.id
    assert event.title == "Team meeting"
    assert event.recurrence == Recurrence.weekly
    assert event.is_completed is False


@pytest.mark.asyncio
async def test_birthday_forces_yearly(user, service):
    data = CreateEventData(
        title="Mom's birthday",
        category=Category.birthday,
        recurrence=Recurrence.monthly,  # should be overridden
        next_remind_at=_now(),
    )
    event = await service.create_event(user.id, data)
    assert event.recurrence == Recurrence.yearly


@pytest.mark.asyncio
async def test_anniversary_forces_yearly(user, service):
    data = CreateEventData(
        title="Wedding anniversary",
        category=Category.anniversary,
        recurrence=Recurrence.every_6_months,  # should be overridden
        next_remind_at=_now(),
    )
    event = await service.create_event(user.id, data)
    assert event.recurrence == Recurrence.yearly


@pytest.mark.asyncio
async def test_get_event(user, service):
    data = CreateEventData(
        title="Dentist", category=Category.personal, recurrence=Recurrence.every_6_months, next_remind_at=_now()
    )
    created = await service.create_event(user.id, data)
    fetched = await service.get_event(user.id, created.id)
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_event_other_user_raises(user, service, db_session):
    other = await UserRepository(db_session).create(email="other@example.com", password="hashed")
    data = CreateEventData(
        title="Private", category=Category.personal, recurrence=Recurrence.monthly, next_remind_at=_now()
    )
    event = await service.create_event(user.id, data)

    with pytest.raises(EventNotFoundError):
        await service.get_event(other.id, event.id)


@pytest.mark.asyncio
async def test_list_events(user, service):
    for title, cat in [("A", Category.meeting), ("B", Category.personal), ("C", Category.meeting)]:
        data = CreateEventData(title=title, category=cat, recurrence=Recurrence.weekly, next_remind_at=_now())
        await service.create_event(user.id, data)

    all_events = await service.list_events(user.id)
    assert len(all_events) == 3

    meetings = await service.list_events(user.id, category=Category.meeting)
    assert len(meetings) == 2
    assert all(e.category == Category.meeting for e in meetings)


@pytest.mark.asyncio
async def test_update_event(user, service):
    data = CreateEventData(
        title="Old title", category=Category.personal, recurrence=Recurrence.monthly, next_remind_at=_now()
    )
    event = await service.create_event(user.id, data)
    updated = await service.update_event(user.id, event.id, UpdateEventData(title="New title"))
    assert updated.title == "New title"


@pytest.mark.asyncio
async def test_update_category_to_birthday_forces_yearly(user, service):
    data = CreateEventData(
        title="Event", category=Category.meeting, recurrence=Recurrence.monthly, next_remind_at=_now()
    )
    event = await service.create_event(user.id, data)
    updated = await service.update_event(user.id, event.id, UpdateEventData(category=Category.birthday))
    assert updated.recurrence == Recurrence.yearly


@pytest.mark.asyncio
async def test_delete_event(user, service):
    data = CreateEventData(
        title="To delete", category=Category.personal, recurrence=Recurrence.weekly, next_remind_at=_now()
    )
    event = await service.create_event(user.id, data)
    await service.delete_event(user.id, event.id)

    with pytest.raises(EventNotFoundError):
        await service.get_event(user.id, event.id)


@pytest.mark.asyncio
async def test_delete_other_user_event_raises(user, service, db_session):
    other = await UserRepository(db_session).create(email="other2@example.com", password="hashed")
    data = CreateEventData(
        title="Mine", category=Category.meeting, recurrence=Recurrence.weekly, next_remind_at=_now()
    )
    event = await service.create_event(user.id, data)

    with pytest.raises(EventNotFoundError):
        await service.delete_event(other.id, event.id)
