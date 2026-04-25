from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from reminder.api.dependencies import get_session
from reminder.api.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from reminder.api.settings import api_settings
from reminder.services.auth_service import AuthService, InvalidCredentialsError, InvalidTokenError
from reminder.services.user_service import EmailAlreadyExistsError

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session, api_settings.secret_key)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, svc: AuthService = Depends(_auth_service)) -> TokenResponse:
    try:
        _, tokens = await svc.register(body.email, body.password, name=body.name, timezone=body.timezone)
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, svc: AuthService = Depends(_auth_service)) -> TokenResponse:
    try:
        _, tokens = await svc.login(body.email, body.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, svc: AuthService = Depends(_auth_service)) -> TokenResponse:
    try:
        access_token = await svc.refresh_access_token(body.refresh_token)
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    return TokenResponse(access_token=access_token, refresh_token=body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, svc: AuthService = Depends(_auth_service)) -> None:
    try:
        await svc.logout(body.refresh_token)
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or already revoked token")
