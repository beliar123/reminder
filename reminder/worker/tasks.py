from datetime import datetime, timedelta, timezone

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

    now = datetime.now(tz=timezone.utc)

    event_repo = EventRepository(session)
    events = await event_repo.get_due(now)
    for event in events:
        scheduled_at = event.next_remind_at
        job_id = f"send_reminder:{event.id}:{scheduled_at.isoformat()}"
        await redis.enqueue_job(
            "send_reminder",
            event.id,
            scheduled_at,
            _job_id=job_id,
        )

    history_repo = EventHistoryRepository(session)
    nag_histories = await history_repo.get_due_nags(now)
    for history in nag_histories:
        job_id = f"send_nag:{history.id}:{history.next_nag_at.isoformat()}"
        await redis.enqueue_job(
            "send_nag",
            history.id,
            _job_id=job_id,
        )

    logger.info("poll.completed", reminders=len(events), nags=len(nag_histories))


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

    user_name = user.name or user.email.split("@")[0]

    try:
        await send_reminder_email(
            to=user.email,
            user_name=user_name,
            event_title=event.title,
            scheduled_at=scheduled_at,
            settings=settings,
            event_description=event.description,
        )
    except Exception:
        logger.error("reminder.failed", event_id=event_id, exc_info=True)
        raise

    await history_repo.update(history, notified_at=datetime.now(tz=timezone.utc))
    await session.commit()

    logger.info("reminder.sent", event_id=event_id, user_email=user.email)


async def send_nag(ctx: dict, history_id: int) -> None:
    session = ctx["session"]
    settings: AppSettings = ctx["settings"]

    history_repo = EventHistoryRepository(session)
    history = await history_repo.get_by_id(history_id)
    if history is None:
        return

    if history.completed_at is not None:
        logger.info("nag.skipped", history_id=history_id, reason="completed")
        return

    event_repo = EventRepository(session)
    event = await event_repo.get_by_id(history.event_id)
    if event is None:
        return

    if event.remind_max_attempts is not None and history.attempt_count >= event.remind_max_attempts:
        await history_repo.update(history, next_nag_at=None)
        await session.commit()
        logger.info("nag.skipped", history_id=history_id, reason="max_attempts_reached")
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(event.user_id)
    if user is None:
        return

    user_name = user.name or user.email.split("@")[0]
    now = datetime.now(tz=timezone.utc)

    try:
        await send_reminder_email(
            to=user.email,
            user_name=user_name,
            event_title=event.title,
            scheduled_at=history.scheduled_at,
            settings=settings,
            event_description=event.description,
        )
    except Exception:
        logger.error("nag.failed", history_id=history_id, exc_info=True)
        raise

    new_attempt_count = history.attempt_count + 1
    limit_reached = (
        event.remind_max_attempts is not None
        and new_attempt_count >= event.remind_max_attempts
    )
    next_nag_at = (
        None if limit_reached
        else now + timedelta(minutes=event.remind_interval)
    )

    await history_repo.update(
        history,
        attempt_count=new_attempt_count,
        next_nag_at=next_nag_at,
    )
    await session.commit()

    logger.info("nag.sent", history_id=history_id, attempt=new_attempt_count, user_email=user.email)
