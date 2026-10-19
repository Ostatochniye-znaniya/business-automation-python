from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.auth.schemas import (
    AuthCallbackRequest,
    AuthRefreshRequest,
    PolytechLoginRequest,
    PolytechTokenResponse,
    PolytechVerifyRequest,
    UserMeResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
polytech_router = APIRouter(prefix="/auth_polytech", tags=["auth_polytech"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> AuthService:
    return AuthService(session)


@router.post("/callback")
async def auth_callback(
    service: Annotated[AuthService, Depends(get_service)],
    body: AuthCallbackRequest,
    request: Request,
    response: Response,
) -> dict:
    return await service.callback(body.access, body.refresh, request, response)


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    service: Annotated[AuthService, Depends(get_service)],
    request: Request,
    response: Response,
) -> UserMeResponse:
    data = await service.get_me(request, response)
    return UserMeResponse(**data)


@router.post("/refresh")
async def auth_refresh(
    service: Annotated[AuthService, Depends(get_service)],
    request: Request,
    response: Response,
    body: AuthRefreshRequest | None = None,
) -> dict:
    return await service.refresh(request, response, body)


@router.post("/logout")
async def auth_logout(
    service: Annotated[AuthService, Depends(get_service)],
    request: Request,
    response: Response,
) -> dict:
    return await service.logout(request, response)


# Прямые эндпоинты авторизации Политеха (доступны и по /auth/login, /auth/verify, и по /auth_polytech/...)
@router.post("/login")
@polytech_router.post("/login")
async def polytech_login(
    service: Annotated[AuthService, Depends(get_service)],
    body: PolytechLoginRequest,
) -> dict:
    return await service.login_polytech(body.login, body.password)


@router.post("/verify", response_model=PolytechTokenResponse)
@polytech_router.post("/verify", response_model=PolytechTokenResponse)
async def polytech_verify(
    service: Annotated[AuthService, Depends(get_service)],
    body: PolytechVerifyRequest,
) -> PolytechTokenResponse:
    res = await service.verify_polytech(body.login, body.code)
    return PolytechTokenResponse(**res)