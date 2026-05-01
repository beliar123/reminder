from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from reminder.api.dependencies import get_current_user, get_session
from reminder.api.schemas.events import CreateEventRequest, EventResponse, UpdateEventRequest
from reminder.enums import Category
from reminder.models.user import User
from reminder.services.event_service import CreateEventData, EventNotFoundError, EventService, UpdateEventData

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: CreateEventRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    svc = EventService(session)
    event = await svc.create_event(
        current_user.id,
        CreateEventData(
            title=body.title,
            description=body.description,
            category=body.category,
            recurrence=body.recurrence,
            next_remind_at=body.next_remind_at,
            remind_interval=body.remind_interval,
            remind_max_attempts=body.remind_max_attempts,
        ),
    )
    return EventResponse.model_validate(event)


@router.get("", response_model=list[EventResponse])
async def list_events(
    category: Category | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EventResponse]:
    svc = EventService(session)
    events = await svc.list_events(current_user.id, category=category)
    return [EventResponse.model_validate(e) for e in events]


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    svc = EventService(session)
    try:
        event = await svc.get_event(current_user.id, event_id)
    except EventNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return EventResponse.model_validate(event)


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    body: UpdateEventRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventResponse:
    svc = EventService(session)
    try:
        event = await svc.update_event(
            current_user.id,
            event_id,
            UpdateEventData(
                title=body.title,
                description=body.description,
                category=body.category,
                recurrence=body.recurrence,
                next_remind_at=body.next_remind_at,
                remind_interval=body.remind_interval,
                remind_max_attempts=body.remind_max_attempts,
            ),
        )
    except EventNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return EventResponse.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = EventService(session)
    try:
        await svc.delete_event(current_user.id, event_id)
    except EventNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
