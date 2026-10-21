from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.dependencies import get_db_session
from app.modules.users.auth_service import AuthService
from app.modules.users.dependencies import get_current_user
from app.modules.users.schemas import DevelopmentLogin, UserRead

router = APIRouter(prefix="/auth", tags=["authentication"])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Config = Annotated[Settings, Depends(get_settings)]


@router.get("/dev-users", response_model=list[UserRead])
async def dev_users(session: Session, settings: Config):
    return await AuthService(session).development_users(settings)


@router.post("/dev-login", response_model=UserRead)
async def dev_login(data: DevelopmentLogin, response: Response, session: Session, settings: Config):
    user, token = await AuthService(session).login(data.user_id, settings)
    response.set_cookie("dev_session", token, httponly=True, samesite="strict", max_age=8 * 3600)
    return user


@router.get("/me", response_model=UserRead)
async def me(actor: Annotated[UserRead, Depends(get_current_user)]):
    return actor


@router.post("/logout", status_code=204)
async def logout(
    response: Response, session: Session, dev_session: Annotated[str | None, Cookie()] = None
):
    await AuthService(session).logout(dev_session)
    response.delete_cookie("dev_session")
