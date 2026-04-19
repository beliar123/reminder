from datetime import datetime

from pydantic import BaseModel

from reminder.enums import Category, Recurrence


class CreateEventRequest(BaseModel):
    title: str
    description: str | None = None
    category: Category
    recurrence: Recurrence
    next_remind_at: datetime


class UpdateEventRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    category: Category | None = None
    recurrence: Recurrence | None = None
    next_remind_at: datetime | None = None


class EventResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    category: Category
    recurrence: Recurrence
    next_remind_at: datetime | None
    is_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}
