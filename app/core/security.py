from app.core.exceptions import FeatureNotImplementedError
from app.modules.users.schemas import UserRead


async def authenticate_token(token: str) -> UserRead:
    """Boundary for future university authentication."""
    # TODO: university SSO protocol and identity mapping are unknown.
    raise FeatureNotImplementedError("University authentication is not configured")
