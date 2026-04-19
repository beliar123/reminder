from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from reminder.api.dependencies import get_current_user, get_session
from reminder.api.schemas.history import CompleteHistoryRequest, HistoryPage, HistoryResponse
from reminder.models.user import User
from reminder.repositories.event_history_repository import EventHistoryRepository
from reminder.services.event_history_service import EventHistoryService, EventNotFoundError, HistoryNotFoundError

router = APIRouter(prefix="/events", tags=["history"])

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


@router.get("/{event_id}/history", response_model=HistoryPage)
async def list_history(
    event_id: int,
    cursor: int | None = None,
    limit: int = _DEFAULT_LIMIT,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> HistoryPage:
    if limit < 1 or limit > _MAX_LIMIT:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"limit must be 1–{_MAX_LIMIT}")

    svc = EventHistoryService(session)
    try:
        # Ownership check via service; then paginated fetch via repo
        await svc.list_history(current_user.id, event_id)  # validates ownership
    except EventNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    repo = EventHistoryRepository(session)
    items = await repo.list_by_event_paginated(event_id, cursor=cursor, limit=limit)
    next_cursor = items[-1].id if len(items) == limit else None
    return HistoryPage(
        items=[HistoryResponse.model_validate(h) for h in items],
        next_cursor=next_cursor,
    )


@router.post("/{event_id}/history/{history_id}/complete", response_model=HistoryResponse)
async def complete_history(
    event_id: int,
    history_id: int,
    body: CompleteHistoryRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> HistoryResponse:
    svc = EventHistoryService(session)
    try:
        history = await svc.mark_completed(current_user.id, history_id, notes=body.notes)
    except HistoryNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History record not found")
    return HistoryResponse.model_validate(history)
