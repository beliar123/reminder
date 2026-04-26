from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from string import Template

import aiosmtplib

from reminder.worker.settings import AppSettings


def _load_template(settings: AppSettings) -> Template:
    path = Path(settings.email_template_path)
    if not path.is_absolute() and not path.exists():
        path = Path(__file__).parent / "templates" / "reminder_email.html"
    return Template(path.read_text(encoding="utf-8"))


async def send_reminder_email(
    to: str,
    user_name: str,
    event_title: str,
    scheduled_at: datetime,
    settings: AppSettings,
    event_description: str | None = None,
) -> None:
    scheduled_date = scheduled_at.strftime("%d.%m.%Y")
    scheduled_time = scheduled_at.strftime("%H:%M UTC")

    if event_description:
        description_block = (
            f'<p style="margin:10px 0 0;font-size:13px;color:#a39e94;line-height:1.6;">'
            f"{event_description}</p>"
        )
    else:
        description_block = ""

    template = _load_template(settings)
    html_body = template.substitute(
        user_name=user_name,
        event_title=event_title,
        description_block=description_block,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
    )

    plain_body = (
        f"Привет, {user_name}!\n\n"
        f"Напоминание: {event_title}\n"
        + (f"{event_description}\n\n" if event_description else "\n")
        + f"Запланировано на: {scheduled_date} {scheduled_time}"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Напоминание: {event_title}"
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )
