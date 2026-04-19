from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from reminder.api.dependencies import get_current_user, get_session
from reminder.api.schemas.users import UpdateUserRequest, UserResponse
from reminder.models.user import User
from reminder.services.user_service import EmailAlreadyExistsError, UpdateUserData, UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    svc = UserService(session)
    data = UpdateUserData(
        name=body.name,
        email=str(body.email) if body.email else None,
        timezone=body.timezone,
        password=body.password,
    )
    try:
        user = await svc.update_user(current_user.id, data)
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
    return UserResponse.model_validate(user)
