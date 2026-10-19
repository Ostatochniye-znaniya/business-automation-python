import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.modules.auth.models import AuthSession
from app.modules.auth.schemas import AuthRefreshRequest
from app.modules.users.models import User

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.admin_api_base = os.getenv(
            "ADMIN_API_BASE_URL", "https://admin.kd.mospolytech.ru"
        ).rstrip("/")

    @staticmethod
    def decode_token(token: str) -> dict[str, Any]:
        """Декодирует JWT без проверки подписи (проверку делает Admin API)."""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as ex:
            logger.warning("Failed to decode JWT: %s", ex)
            return {}

    @classmethod
    def extract_user_id(cls, token: str) -> str | None:
        payload = cls.decode_token(token)
        for key in ("user_id", "sub", "id"):
            val = payload.get(key)
            if val:
                return str(val)
        for k, v in payload.items():
            if k.endswith("/nameidentifier") and v:
                return str(v)
        return None

    async def fetch_admin_user_profile(self, access_token: str) -> dict[str, Any] | None:
        """Запрашивает профиль пользователя в Admin API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(
                    f"{self.admin_api_base}/api/v1/users/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if res.status_code == 200:
                    return res.json()
                logger.warning(
                    "Admin API /users/me returned status %s: %s",
                    res.status_code,
                    res.text,
                )
                return None
        except Exception as ex:
            logger.error("Exception fetching user profile from Admin API: %s", ex)
            return None

    async def refresh_with_admin_api(
        self, access: str, refresh: str, user_id: str
    ) -> dict[str, str] | None:
        """Обновляет токен через Admin API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {
                    "user_id": user_id,
                    "userID": user_id,
                    "access_token": access,
                    "refresh_token": refresh,
                }
                res = await client.post(
                    f"{self.admin_api_base}/api/v1/users/refresh", json=payload
                )
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "access_token": data.get("access_token", ""),
                        "refresh_token": data.get("refresh_token", ""),
                    }
                logger.error(
                    "Admin API refresh failed (%s): %s", res.status_code, res.text
                )
                return None
        except Exception as ex:
            logger.error("Exception during token refresh with Admin API: %s", ex)
            return None

    async def login_polytech(self, login: str, password: str) -> dict[str, Any]:
        """Прямой вызов API Политеха для отправки кода подтверждения."""
        endpoint = f"{self.admin_api_base}/api/v1/users/login"
        payload = {
            "login": login,
            "raw_password": password,
            "service_name": "empl_eval_sys",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code >= 400:
                    raise HTTPException(
                        status_code=res.status_code,
                        detail=f"Auth API error: {res.text}",
                    )
                return {"status": "OK"}
        except HTTPException:
            raise
        except Exception as ex:
            logger.error("Polytech login failed: %s", ex)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to communicate with Auth API: {ex}",
            )

    async def verify_polytech(self, login: str, code: Any) -> dict[str, str]:
        """Прямой вызов API Политеха для проверки кода и получения токенов."""
        endpoint = f"{self.admin_api_base}/api/v1/users/verification_auth_code"
        code_str = str(code)
        payload = {
            "login": login,
            "code": code_str,
            "service_name": "empl_eval_sys",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code >= 400:
                    raise HTTPException(
                        status_code=res.status_code,
                        detail=f"Auth API error: {res.text}",
                    )
                data = res.json()
                return {
                    "user_id": str(data.get("user_id", "")),
                    "access_token": data.get("access_token", ""),
                    "refresh_token": data.get("refresh_token", ""),
                }
        except HTTPException:
            raise
        except Exception as ex:
            logger.error("Polytech verify failed: %s", ex)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to communicate with Auth API: {ex}",
            )

    @staticmethod
    def set_cookie(
        response: Response,
        key: str,
        value: str,
        secure: bool = False,
        httponly: bool = True,
    ) -> None:
        response.set_cookie(
            key=key,
            value=value,
            httponly=httponly,
            secure=secure,
            samesite="lax",
            path="/",
            max_age=30 * 24 * 3600,
        )

    @staticmethod
    def clear_cookie(response: Response, key: str) -> None:
        response.delete_cookie(key=key, path="/", httponly=True, samesite="lax")
        response.delete_cookie(key=key, path="/", httponly=False, samesite="lax")

    def _get_token_from_request(self, request: Request) -> str | None:
        cookie_token = request.cookies.get("access_token")
        if cookie_token and cookie_token.strip():
            return cookie_token.strip()
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()
        return None

    def _get_refresh_from_request(self, request: Request) -> str | None:
        cookie_refresh = request.cookies.get("refresh_token")
        if cookie_refresh and cookie_refresh.strip():
            return cookie_refresh.strip()
        return None

    async def callback(
        self,
        access: str,
        refresh: str,
        request: Request,
        response: Response,
    ) -> dict[str, Any]:
        """Обработка обратного вызова авторизации, сохранение сессии и синхронизация пользователя."""
        if not access or not refresh:
            raise HTTPException(status_code=400, detail="Missing tokens")

        user_id = self.extract_user_id(access)
        user_profile = await self.fetch_admin_user_profile(access)

        if not user_id and user_profile:
            user_id = str(user_profile.get("id", ""))

        if not user_id:
            user_id = "unknown"

        # Синхронизация пользователя в БД
        if user_profile:
            email = user_profile.get("email") or None
            surname = user_profile.get("surname", "") or ""
            name = user_profile.get("name", "") or ""
            patronymic = user_profile.get("patronymic", "") or ""
            full_name = f"{surname} {name} {patronymic}".strip() or "Пользователь"

            # Ищем по external_id или email
            q = select(User).where(
                (User.external_id == user_id)
                | (User.email == email if email else False)
            )
            result = await self.session.execute(q)
            db_user = result.scalars().first()

            if not db_user:
                db_user = User(
                    external_id=user_id if user_id != "unknown" else None,
                    full_name=full_name,
                    email=email,
                    is_active=True,
                    role=UserRole.GUEST,
                )
                self.session.add(db_user)
            else:
                if full_name and db_user.full_name != full_name:
                    db_user.full_name = full_name
                if not db_user.external_id and user_id != "unknown":
                    db_user.external_id = user_id
                if not db_user.email and email:
                    db_user.email = email

        device_id = request.cookies.get("device_id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        user_agent = request.headers.get("user-agent", "")
        ip_address = request.client.host if request.client else None

        # Управление сессией AuthSession
        sess_q = select(AuthSession).where(
            AuthSession.user_id == user_id, AuthSession.device_id == device_id
        )
        sess_res = await self.session.execute(sess_q)
        auth_session = sess_res.scalar_one_or_none()

        if auth_session:
            auth_session.refresh_token = refresh
            auth_session.user_agent = user_agent
            auth_session.ip_address = ip_address
            auth_session.updated_at = now
        else:
            auth_session = AuthSession(
                id=str(uuid.uuid4()),
                user_id=user_id,
                device_id=device_id,
                refresh_token=refresh,
                user_agent=user_agent,
                ip_address=ip_address,
                created_at=now,
                updated_at=now,
            )
            self.session.add(auth_session)

        await self.session.commit()
        await self.session.refresh(auth_session)

        is_https = request.url.scheme == "https"
        self.set_cookie(response, "access_token", access, secure=is_https)
        self.set_cookie(response, "refresh_token", refresh, secure=is_https)
        self.set_cookie(response, "session_id", auth_session.id, secure=is_https)
        self.set_cookie(response, "device_id", device_id, secure=is_https)

        return {"ok": True, "user_id": user_id}

    async def get_me(self, request: Request, response: Response) -> dict[str, Any]:
        """Возвращает информацию о текущем авторизованном пользователе."""
        access = self._get_token_from_request(request)
        if not access:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_id = self.extract_user_id(access)

        db_user = None
        if user_id and user_id != "unknown":
            q = select(User).where(User.external_id == user_id)
            res = await self.session.execute(q)
            db_user = res.scalar_one_or_none()

        if not db_user:
            profile = await self.fetch_admin_user_profile(access)

            # Если токен устарел во внешней системе — пробуем обновить
            if profile is None:
                refresh_token = self._get_refresh_from_request(request)
                if not refresh_token:
                    raise HTTPException(
                        status_code=401,
                        detail="Token expired and refresh token missing",
                    )

                refreshed = await self.refresh_with_admin_api(
                    access, refresh_token, user_id or ""
                )
                if not refreshed or not refreshed.get("access_token"):
                    raise HTTPException(status_code=401, detail="Failed to refresh token")

                access = refreshed["access_token"]
                new_refresh = refreshed.get("refresh_token")
                is_https = request.url.scheme == "https"
                self.set_cookie(response, "access_token", access, secure=is_https)
                if new_refresh:
                    self.set_cookie(
                        response, "refresh_token", new_refresh, secure=is_https
                    )

                new_user_id = self.extract_user_id(access)
                if new_user_id:
                    user_id = new_user_id

                profile = await self.fetch_admin_user_profile(access)
                if not profile:
                    raise HTTPException(
                        status_code=401,
                        detail="Failed to authenticate after token refresh",
                    )

            if not user_id or user_id == "unknown":
                user_id = str(profile.get("id", ""))

            email = profile.get("email") or None
            if email:
                q = select(User).where(
                    (User.email == email) | (User.external_id == user_id)
                )
                res = await self.session.execute(q)
                db_user = res.scalars().first()

            if not db_user and email:
                surname = profile.get("surname", "") or ""
                name = profile.get("name", "") or ""
                patronymic = profile.get("patronymic", "") or ""
                full_name = f"{surname} {name} {patronymic}".strip() or "Пользователь"

                db_user = User(
                    external_id=user_id if user_id != "unknown" else None,
                    full_name=full_name,
                    email=email,
                    is_active=True,
                    role=UserRole.GUEST,
                )
                self.session.add(db_user)
                await self.session.commit()
                await self.session.refresh(db_user)
            elif db_user and not db_user.external_id and user_id != "unknown":
                db_user.external_id = user_id
                await self.session.commit()

        if not db_user:
            raise HTTPException(
                status_code=401, detail="User not found in local database"
            )

        # Разбор ФИО
        name_parts = (db_user.full_name or "").split()
        last_name = name_parts[0] if len(name_parts) > 0 else ""
        first_name = name_parts[1] if len(name_parts) > 1 else ""
        patronymic = name_parts[2] if len(name_parts) > 2 else ""

        role_str = (
            db_user.role.value
            if hasattr(db_user.role, "value")
            else str(db_user.role)
        )
        roles = [role_str] if role_str else ["GUEST"]

        return {
            "id": db_user.id,
            "external_id": db_user.external_id,
            "name": first_name or db_user.full_name,
            "full_name": db_user.full_name,
            "first_name": first_name,
            "last_name": last_name,
            "surname": last_name,
            "patronymic": patronymic,
            "email": db_user.email,
            "mail_box": db_user.email,
            "status_id": None,
            "status": role_str,
            "faculty_id": None,
            "faculty": None,
            "role": role_str,
            "roles": roles,
            "access_token": access,
            "refresh_token": self._get_refresh_from_request(request),
        }

    async def refresh(
        self,
        request: Request,
        response: Response,
        body: AuthRefreshRequest | None = None,
    ) -> dict[str, str]:
        """Обновление токенов доступа."""
        access = (
            body.access_token
            if body and body.access_token
            else self._get_token_from_request(request)
        )
        refresh = (
            body.refresh_token
            if body and body.refresh_token
            else self._get_refresh_from_request(request)
        )
        user_id = body.user_id if body and body.user_id else None

        if not access or not refresh:
            raise HTTPException(
                status_code=400, detail="Missing access or refresh token"
            )

        if not user_id:
            user_id = self.extract_user_id(access) or ""

        tokens = await self.refresh_with_admin_api(access, refresh, user_id)
        if not tokens or not tokens.get("access_token"):
            raise HTTPException(status_code=401, detail="Refresh failed")

        is_https = request.url.scheme == "https"
        self.set_cookie(
            response, "access_token", tokens["access_token"], secure=is_https
        )
        if tokens.get("refresh_token"):
            self.set_cookie(
                response, "refresh_token", tokens["refresh_token"], secure=is_https
            )

        # Обновляем сессию в БД если есть device_id
        device_id = request.cookies.get("device_id")
        if device_id and user_id:
            sess_q = select(AuthSession).where(
                AuthSession.user_id == user_id, AuthSession.device_id == device_id
            )
            sess_res = await self.session.execute(sess_q)
            auth_session = sess_res.scalar_one_or_none()
            if auth_session:
                auth_session.refresh_token = tokens.get("refresh_token", refresh)
                auth_session.updated_at = datetime.now(timezone.utc)
                await self.session.commit()

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token", refresh),
        }

    async def logout(self, request: Request, response: Response) -> dict[str, bool]:
        """Выход пользователя: инвалидация сессии в БД и очистка кук."""
        session_id = request.cookies.get("session_id")
        device_id = request.cookies.get("device_id")

        if session_id or device_id:
            cond = []
            if session_id:
                cond.append(AuthSession.id == session_id)
            if device_id:
                cond.append(AuthSession.device_id == device_id)
            if cond:
                await self.session.execute(delete(AuthSession).where(*cond))
                await self.session.commit()

        for cookie_key in (
            "access_token",
            "refresh_token",
            "session_id",
            "device_id",
            "is_authenticated",
            "user_data",
        ):
            self.clear_cookie(response, cookie_key)

        for cookie_key in request.cookies.keys():
            self.clear_cookie(response, cookie_key)

        return {"ok": True}