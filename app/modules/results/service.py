from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import KnowledgeTestStatus, ParticipationStatus, UserRole
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.permissions import MANAGERS, audit, require_role
from app.modules.results.models import TestResult
from app.modules.results.schemas import TestResultCreate
from app.modules.students.models import Student
from app.modules.testing.workflow import TestingWorkflow
from app.modules.users.schemas import UserRead


class ResultService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def participation_counts(self, test_ids: set[int]) -> dict[int, int]:
        from sqlalchemy import func

        return dict(
            (
                await self.session.execute(
                    select(TestResult.knowledge_test_id, func.count(TestResult.id))
                    .where(
                        TestResult.knowledge_test_id.in_(test_ids),
                        TestResult.participation_status == ParticipationStatus.PASSED,
                    )
                    .group_by(TestResult.knowledge_test_id)
                )
            ).all()
        )

    async def has_student_results(self, student_id: int) -> bool:
        return bool(
            await self.session.scalar(
                select(TestResult.id).where(TestResult.student_id == student_id).limit(1)
            )
        )

    async def get_by_id(self, entity_id: int) -> TestResult:
        entity = await self.session.get(TestResult, entity_id)
        if entity is None:
            raise NotFoundError("TestResult not found")
        return entity

    async def get_by_test(
        self, knowledge_test_id: int, offset: int = 0, limit: int = 100
    ) -> list[TestResult]:
        return list(
            (
                await self.session.scalars(
                    select(TestResult)
                    .where(TestResult.knowledge_test_id == knowledge_test_id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )

    async def save_result(self, data: TestResultCreate, actor: UserRead) -> TestResult:
        require_role(actor, MANAGERS | {UserRole.TEACHER})
        test = await TestingWorkflow(self.session).get_test(
            data.knowledge_test_id, actor, write=True
        )
        if test.status == KnowledgeTestStatus.CANCELLED or test.agreement_status != "AGREED":
            raise ConflictError("Проверка должна быть согласована с преподавателем")
        student = await self.session.get(Student, data.student_id)
        if student is None or student.group_id != test.group_id:
            raise ValidationError("Студент не относится к группе проверки")
        if data.participation_status == ParticipationStatus.PASSED and data.testing_result is None:
            raise ValidationError("Укажите результат прошедшего тестирование студента")
        if (
            data.participation_status != ParticipationStatus.PASSED
            and data.testing_result is not None
        ):
            raise ValidationError("Для отсутствующего или недопущенного результат не указывается")
        from app.modules.reports.service import ReportService

        reports = await ReportService(self.session).get_by_test(test.id)
        if reports and reports[0].electronic_status in {"SUBMITTED", "APPROVED"}:
            raise ConflictError("Отзовите отчёт с проверки перед изменением результатов")
        entity = await self.session.scalar(
            select(TestResult).where(
                TestResult.knowledge_test_id == test.id, TestResult.student_id == student.id
            )
        )
        if entity is None:
            entity = TestResult()
            self.session.add(entity)
        for key, value in data.model_dump().items():
            setattr(entity, key, value)
        test.status = KnowledgeTestStatus.IN_PROGRESS
        audit(self.session, actor, "result.save", test.id)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def complete(self, test_id: int, actor: UserRead):
        require_role(actor, MANAGERS | {UserRole.TEACHER})
        test = await TestingWorkflow(self.session).get_test(test_id, actor, write=True)
        if test.agreement_status != "AGREED" or test.status == KnowledgeTestStatus.CANCELLED:
            raise ConflictError("Проверка не согласована или отменена")
        students = set(
            (
                await self.session.scalars(
                    select(Student.id).where(Student.group_id == test.group_id)
                )
            ).all()
        )
        results = await self.get_by_test(test_id, limit=100000)
        if not students or students != {result.student_id for result in results}:
            raise ValidationError("Заполните статус участия каждого студента группы")
        test.status = KnowledgeTestStatus.COMPLETED
        audit(self.session, actor, "testing.complete", test.id)
        await self.session.commit()
        return test
