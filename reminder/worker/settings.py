from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"

    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    smtp_from: str
    log_level: str = "info"
    log_format: str = "console"
    email_template_path: str = "reminder/worker/templates/reminder_email.html"

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}
