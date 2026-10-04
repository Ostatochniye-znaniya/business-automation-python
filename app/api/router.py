from fastapi import APIRouter

from app.modules.periods.router import router as periods_router

# Domain routes are included as their use cases are implemented.
api_router = APIRouter()
api_router.include_router(periods_router)
