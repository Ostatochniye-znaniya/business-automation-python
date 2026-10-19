from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.enums import UserRole
from app.core.exceptions import ForbiddenError
from app.modules.users.schemas import UserRead


async def get_dev_user(settings: Annotated[Settings, Depends(get_settings)]) -> UserRead:
    """Opt-in development identity; never allowed outside development."""
    if settings.APP_ENV != "development":
        raise ForbiddenError("Development identity is disabled")
    return UserRead(id=1, full_name="Development user", role=UserRole.GUEST)
