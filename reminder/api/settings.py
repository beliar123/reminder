from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    database_url: str
    secret_key: str
    cors_origins: list[str] = ["*"]
    log_level: str = "info"
    log_format: str = "console"

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


api_settings = ApiSettings()
