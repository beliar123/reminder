from datetime import datetime

from pydantic import BaseModel


class HistoryResponse(BaseModel):
    id: int
    event_id: int
    scheduled_at: datetime
    reminded_at: datetime
    completed_at: datetime | None
    notes: str | None

    model_config = {"from_attributes": True}


class HistoryPage(BaseModel):
    items: list[HistoryResponse]
    next_cursor: int | None


class CompleteHistoryRequest(BaseModel):
    notes: str | None = None
