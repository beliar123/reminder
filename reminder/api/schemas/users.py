from datetime import datetime
from zoneinfo import ZoneInfoNotFoundError, available_timezones

from pydantic import BaseModel, EmailStr, field_validator


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None
    timezone: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateUserRequest(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    timezone: str | None = None
    password: str | None = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in available_timezones():
            raise ValueError(f"Unknown IANA timezone: {v!r}")
        return v
