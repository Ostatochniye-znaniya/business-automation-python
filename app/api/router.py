from fastapi import APIRouter

from app.modules.dashboard.router import router as dashboard_router
from app.modules.departments.router import router as departments_router
from app.modules.disciplines.router import router as disciplines_router
from app.modules.groups.router import programs_router
from app.modules.groups.router import router as groups_router
from app.modules.periods.router import router as periods_router
from app.modules.reports.router import router as reports_router
from app.modules.results.router import router as results_router
from app.modules.students.router import router as students_router
from app.modules.testing.router import router as testing_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
for router in (
    users_router,
    departments_router,
    periods_router,
    groups_router,
    programs_router,
    disciplines_router,
    students_router,
    testing_router,
    results_router,
    reports_router,
    dashboard_router,
):
    api_router.include_router(router)
