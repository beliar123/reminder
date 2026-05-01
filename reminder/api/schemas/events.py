from datetime import datetime

from pydantic import BaseModel

from reminder.enums import Category, Recurrence


class CreateEventRequest(BaseModel):
    title: str
    description: str | None = None
    category: Category
    recurrence: Recurrence
    next_remind_at: datetime
    remind_interval: int | None = None
    remind_max_attempts: int | None = None


class UpdateEventRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    category: Category | None = None
    recurrence: Recurrence | None = None
    next_remind_at: datetime | None = None
    remind_interval: int | None = None
    remind_max_attempts: int | None = None


class EventResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    category: Category
    recurrence: Recurrence
    next_remind_at: datetime | None
    is_completed: bool
    remind_interval: int | None
    remind_max_attempts: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
