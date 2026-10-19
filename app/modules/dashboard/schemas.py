from pydantic import BaseModel

from app.modules.disciplines.schemas import DashboardStatistics as DisciplineStatistics
from app.modules.groups.schemas import DashboardStatistics as GroupStatistics
from app.modules.reports.schemas import ReportStatistics


class PeriodSummary(BaseModel):
    id: int
    name: str


class DepartmentSummary(BaseModel):
    id: int
    name: str
    groups: GroupStatistics
    disciplines: DisciplineStatistics
    reports: ReportStatistics
    all_submitted: bool | None = None


class DashboardRead(BaseModel):
    period: PeriodSummary
    departments: list[DepartmentSummary]
