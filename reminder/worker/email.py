from datetime import datetime
from email.mime.text import MIMEText

import aiosmtplib

from reminder.worker.settings import AppSettings


async def send_reminder_email(
    to: str,
    event_title: str,
    scheduled_at: datetime,
    settings: AppSettings,
) -> None:
    msg = MIMEText(f"Напоминание: {event_title}\nЗапланировано на: {scheduled_at.strftime('%Y-%m-%d %H:%M')} UTC")
    msg["Subject"] = f"Напоминание: {event_title}"
    msg["From"] = settings.smtp_from
    msg["To"] = to

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )
