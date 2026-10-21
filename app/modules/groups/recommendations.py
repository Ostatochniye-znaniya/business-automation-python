import csv
import io
import logging
from datetime import UTC, date, datetime

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import TestingPeriodStatus, UserRole
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.departments.models import Department
from app.modules.groups.models import GroupPeriod, StudyGroup, StudyProgram
from app.modules.groups.recommendation_models import GroupRecommendation, RecommendationHistory
from app.modules.groups.recommendation_schemas import (
    RecommendationHistoryRead,
    RecommendationRead,
    RecommendationSave,
)
from app.modules.periods.models import TestingPeriod
from app.modules.users.models import User
from app.modules.users.schemas import UserRead

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_recommendations(
        self,
        *,
        period_id: int | None = None,
        group_id: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[RecommendationRead]:
        statement = (
            select(GroupRecommendation, User.full_name)
            .join(User, User.id == GroupRecommendation.changed_by_id)
            .where(GroupRecommendation.recommended.is_(True))
        )
        if period_id is not None:
            statement = statement.where(GroupRecommendation.period_id == period_id)
        if group_id is not None:
            statement = statement.where(GroupRecommendation.group_id == group_id)
        records = (
            await self.session.execute(
                statement.order_by(GroupRecommendation.id).offset(offset).limit(limit)
            )
        ).all()
        return [self.read(record, name) for record, name in records]

    @staticmethod
    def read(record: GroupRecommendation, name: str) -> RecommendationRead:
        return RecommendationRead(
            id=record.id,
            group_id=record.group_id,
            period_id=record.period_id,
            recommended=record.recommended,
            version=record.version,
            changed_by_id=record.changed_by_id,
            changed_by_name=name,
            changed_at=record.changed_at,
        )

    async def save(self, data: RecommendationSave, actor: UserRead) -> list[RecommendationRead]:
        if not actor.is_active or actor.role not in {UserRole.ADMIN, UserRole.LPR}:
            raise ForbiddenError("Изменять рекомендации могут только ЛПР и администратор")
        changes = sorted(data.changes, key=lambda item: (item.period_id, item.group_id))
        pairs = [(change.period_id, change.group_id) for change in changes]
        try:
            # Lock in a stable order, including pairs with no recommendation yet.
            memberships = (
                await self.session.scalars(
                    select(GroupPeriod)
                    .where(tuple_(GroupPeriod.period_id, GroupPeriod.group_id).in_(pairs))
                    .order_by(GroupPeriod.period_id, GroupPeriod.group_id)
                    .with_for_update()
                )
            ).all()
            if len(memberships) != len(changes):
                raise ValidationError("Группа не участвует в выбранном периоде")
            periods = (
                await self.session.scalars(
                    select(TestingPeriod)
                    .where(TestingPeriod.id.in_({change.period_id for change in changes}))
                    .order_by(TestingPeriod.id)
                    .with_for_update()
                )
            ).all()
            if any(
                period.status == TestingPeriodStatus.CLOSED or period.end_date < date.today()
                for period in periods
            ):
                raise ConflictError("Рекомендации закрытого или прошедшего периода изменять нельзя")
            existing = (
                await self.session.scalars(
                    select(GroupRecommendation)
                    .where(
                        tuple_(GroupRecommendation.period_id, GroupRecommendation.group_id).in_(
                            pairs
                        )
                    )
                    .order_by(GroupRecommendation.period_id, GroupRecommendation.group_id)
                    .with_for_update()
                )
            ).all()
            records = {(record.period_id, record.group_id): record for record in existing}
            names = dict(
                (
                    await self.session.execute(
                        select(User.id, User.full_name).where(
                            User.id.in_({record.changed_by_id for record in existing})
                        )
                    )
                ).all()
            )
            result = []
            changed = []
            for change in changes:
                record = records.get((change.period_id, change.group_id))
                if (record.version if record else 0) != change.expected_version:
                    raise ConflictError(
                        "Список изменён другим пользователем. Обновите данные и повторите выбор"
                    )
                if record is None and not change.recommended:
                    continue
                if record is not None and record.recommended == change.recommended:
                    result.append(record)
                    continue
                now = datetime.now(UTC).replace(tzinfo=None)
                if record is None:
                    record = GroupRecommendation(
                        group_id=change.group_id,
                        period_id=change.period_id,
                        recommended=change.recommended,
                        version=1,
                        changed_by_id=actor.id,
                        changed_at=now,
                    )
                    self.session.add(record)
                else:
                    record.recommended = change.recommended
                    record.version += 1
                    record.changed_by_id = actor.id
                    record.changed_at = now
                changed.append(record)
                result.append(record)
            await self.session.flush()
            self.session.add_all(
                [
                    RecommendationHistory(
                        recommendation_id=record.id,
                        recommended=record.recommended,
                        version=record.version,
                        changed_by_id=actor.id,
                        changed_at=record.changed_at,
                    )
                    for record in changed
                ]
            )
            names[actor.id] = actor.full_name
            response = [self.read(record, names[record.changed_by_id]) for record in result]
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        logger.info("Recommendations saved: actor_id=%s changes=%s", actor.id, len(changed))
        return response

    async def history(
        self, group_id: int, period_id: int | None = None, offset: int = 0, limit: int = 100
    ) -> list[RecommendationHistoryRead]:
        if await self.session.get(StudyGroup, group_id) is None:
            raise NotFoundError("Группа не найдена")
        statement = (
            select(RecommendationHistory, GroupRecommendation, User.full_name, TestingPeriod.name)
            .join(
                GroupRecommendation,
                GroupRecommendation.id == RecommendationHistory.recommendation_id,
            )
            .join(User, User.id == RecommendationHistory.changed_by_id)
            .join(TestingPeriod, TestingPeriod.id == GroupRecommendation.period_id)
            .where(GroupRecommendation.group_id == group_id)
        )
        if period_id is not None:
            statement = statement.where(GroupRecommendation.period_id == period_id)
        records = (
            await self.session.execute(
                statement.order_by(RecommendationHistory.id.desc()).offset(offset).limit(limit)
            )
        ).all()
        return [
            RecommendationHistoryRead(
                id=event.id,
                group_id=record.group_id,
                period_id=record.period_id,
                recommended=event.recommended,
                version=event.version,
                changed_by_id=event.changed_by_id,
                changed_by_name=name,
                changed_at=event.changed_at,
                period_name=period_name,
            )
            for event, record, name, period_name in records
        ]

    async def export(
        self, period_id: int, faculty_id: int | None = None, study_program_id: int | None = None
    ) -> str:
        period = await self.session.get(TestingPeriod, period_id)
        if period is None:
            raise NotFoundError("Период не найден")
        statement = (
            select(
                StudyGroup,
                StudyProgram.name,
                Department.name,
                User.full_name,
                GroupRecommendation.changed_at,
            )
            .join(GroupRecommendation, GroupRecommendation.group_id == StudyGroup.id)
            .outerjoin(StudyProgram, StudyProgram.id == StudyGroup.study_program_id)
            .outerjoin(Department, Department.id == StudyProgram.faculty_id)
            .join(User, User.id == GroupRecommendation.changed_by_id)
            .where(
                GroupRecommendation.period_id == period_id,
                GroupRecommendation.recommended.is_(True),
            )
            .order_by(StudyGroup.name, StudyGroup.id)
        )
        if faculty_id is not None:
            statement = statement.where(StudyProgram.faculty_id == faculty_id)
        if study_program_id is not None:
            statement = statement.where(StudyGroup.study_program_id == study_program_id)
        records = (await self.session.execute(statement)).all()
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(
            [
                "Группа",
                "Направление",
                "Факультет / институт",
                "Курс",
                "Учебный год",
                "Семестр",
                "Рекомендовал",
                "Дата (UTC)",
            ]
        )
        for group, program, faculty, name, timestamp in records:
            course = (
                int(period.academic_year[:4]) - group.admission_year + 1
                if group.admission_year and period.academic_year[:4].isdigit()
                else None
            )

            # Spreadsheet applications must treat imported names as text, never formulas.
            def safe(value):
                text = str(value or "")
                return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text

            writer.writerow(
                [
                    safe(group.name),
                    safe(program),
                    safe(faculty),
                    course if course and course > 0 else "",
                    period.academic_year,
                    period.semester,
                    safe(name),
                    timestamp.isoformat(),
                ]
            )
        return "\ufeff" + output.getvalue()
