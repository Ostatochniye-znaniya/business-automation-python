from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError


@dataclass(frozen=True)
class ExternalIdentity:
    external_id: str


async def authenticate_token(token: str) -> ExternalIdentity:
    """Validate a bearer token against a configured RFC 7662 endpoint."""
    settings = get_settings()
    if not settings.AUTH_INTROSPECTION_URL:
        raise ForbiddenError("Проверка токенов SSO не настроена")
    if not settings.AUTH_INTROSPECTION_URL.startswith("https://"):
        raise ForbiddenError("Адрес проверки токена должен использовать HTTPS")
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            response = await client.post(
                settings.AUTH_INTROSPECTION_URL,
                data={"token": token},
                auth=(
                    settings.AUTH_INTROSPECTION_CLIENT_ID or "",
                    settings.AUTH_INTROSPECTION_CLIENT_SECRET or "",
                ),
            )
            response.raise_for_status()
            payload = response.json()
        if (
            not isinstance(payload, dict)
            or payload.get("active") is not True
            or not isinstance(payload.get("sub"), str)
            or not payload["sub"].strip()
            or len(payload["sub"]) > 128
        ):
            raise ForbiddenError("Недействительный токен")
    except (httpx.HTTPError, ValueError) as exc:
        raise ForbiddenError("Не удалось проверить токен") from exc
    # Identity is matched to the local employee directory by external_id in the dependency.
    return ExternalIdentity(external_id=payload["sub"])
