import structlog
from arq import cron
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from reminder.logging import configure_logging
from reminder.worker.settings import AppSettings
from reminder.worker.tasks import poll_due_reminders, send_reminder

_app_settings = AppSettings()


def _retry_delay(attempt: int) -> float:
    # попытка 1→3s, 2→6s, 3→12s
    return min(3 * (2 ** (attempt - 1)), 12)


async def on_startup(ctx: dict) -> None:
    configure_logging(_app_settings.log_level, _app_settings.log_format)
    logger = structlog.get_logger()
    engine = create_async_engine(_app_settings.database_url)
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)
    ctx["db_engine"] = engine
    ctx["session_factory"] = factory
    ctx["session"] = factory()
    ctx["settings"] = _app_settings
    logger.info("worker.startup")


async def on_shutdown(ctx: dict) -> None:
    structlog.get_logger().info("worker.shutdown")
    await ctx["session"].close()
    await ctx["db_engine"].dispose()


class WorkerSettings:
    functions = [send_reminder]
    cron_jobs = [cron(poll_due_reminders, minute={*range(0, 60)})]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = RedisSettings.from_dsn(_app_settings.redis_url)
    max_tries = 3
    retry_jobs = True
    job_retry_on_fail = True
    retry_delay = _retry_delay
