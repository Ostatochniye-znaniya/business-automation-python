from app.modules.dashboard.schemas import DashboardRead, DepartmentSummary, PeriodSummary
from app.modules.departments.service import DepartmentService
from app.modules.disciplines.service import DisciplineService
from app.modules.groups.service import GroupService
from app.modules.periods.service import PeriodService
from app.modules.reports.service import ReportService


class DashboardService:
    def __init__(
        self,
        periods: PeriodService,
        departments: DepartmentService,
        groups: GroupService,
        disciplines: DisciplineService,
        reports: ReportService,
    ):
        self.periods = periods
        self.departments = departments
        self.groups = groups
        self.disciplines = disciplines
        self.reports = reports

    async def get_dashboard(self, period_id: int) -> DashboardRead:
        period = await self.periods.get_by_id(period_id)
        rows = []
        offset = 0
        while departments := await self.departments.list_departments(offset=offset, limit=100):
            for department in departments:
                rows.append(
                    DepartmentSummary(
                        id=department.id,
                        name=department.name,
                        groups=await self.groups.get_dashboard_statistics(period_id, department.id),
                        disciplines=await self.disciplines.get_dashboard_statistics(
                            period_id, department.id
                        ),
                        reports=await self.reports.get_dashboard_statistics(
                            period_id, department.id
                        ),
                        # TODO: agree faculty/child department aggregation for all_submitted.
                        all_submitted=None,
                    )
                )
            offset += len(departments)
        return DashboardRead(period=PeriodSummary(id=period.id, name=period.name), departments=rows)
