from datetime import datetime, timezone

import structlog
from arq import ArqRedis

from reminder.repositories.event_history_repository import EventHistoryRepository
from reminder.repositories.event_repository import EventRepository
from reminder.repositories.user_repository import UserRepository
from reminder.services.event_history_service import EventHistoryService
from reminder.worker.email import send_reminder_email
from reminder.worker.settings import AppSettings

logger = structlog.get_logger()


async def poll_due_reminders(ctx: dict) -> None:
    session = ctx["session"]
    redis: ArqRedis = ctx["redis"]

    repo = EventRepository(session)
    now = datetime.now(tz=timezone.utc)
    events = await repo.get_due(now)

    for event in events:
        scheduled_at = event.next_remind_at
        job_id = f"send_reminder:{event.id}:{scheduled_at.isoformat()}"
        await redis.enqueue_job(
            "send_reminder",
            event.id,
            scheduled_at,
            _job_id=job_id,
        )

    logger.info("poll.completed", count=len(events))


async def send_reminder(ctx: dict, event_id: int, scheduled_at: datetime) -> None:
    session = ctx["session"]
    settings: AppSettings = ctx["settings"]

    history_repo = EventHistoryRepository(session)
    history = await history_repo.get_by_event_and_scheduled(event_id, scheduled_at)

    if history is None:
        service = EventHistoryService(session)
        history = await service.advance_reminder(event_id)
        await session.commit()

    if history is None or history.notified_at is not None:
        logger.info("reminder.skipped", event_id=event_id, reason="already_delivered")
        return

    event_repo = EventRepository(session)
    event = await event_repo.get_by_id(event_id)
    if event is None:
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(event.user_id)
    if user is None:
        return

    try:
        await send_reminder_email(
            to=user.email,
            event_title=event.title,
            scheduled_at=scheduled_at,
            settings=settings,
        )
    except Exception:
        logger.error("reminder.failed", event_id=event_id, exc_info=True)
        raise

    await history_repo.update(history, notified_at=datetime.now(tz=timezone.utc))
    await session.commit()

    logger.info("reminder.sent", event_id=event_id, user_email=user.email)
