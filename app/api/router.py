from fastapi import APIRouter

from app.modules.periods.router import router as periods_router
from app.modules.students.router import router as students_router

# Domain routes are included as their use cases are implemented.
api_router = APIRouter()
api_router.include_router(periods_router)
api_router.include_router(students_router)
