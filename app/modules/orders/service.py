from pydantic import ValidationError as SchemaValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.permissions import MANAGERS, audit, require_role
from app.modules.orders.models import Order
from app.modules.orders.schemas import OrderCreate, OrderPublication
from app.modules.periods.models import TestingPeriod
from app.modules.reports.service import ReportService
from app.modules.users.schemas import UserRead


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_orders(self, offset: int = 0, limit: int = 100) -> list[Order]:
        return list(
            (
                await self.session.scalars(
                    select(Order).order_by(Order.id.desc()).offset(offset).limit(limit)
                )
            ).all()
        )

    async def get_by_id(self, order_id: int, *, for_update: bool = False) -> Order:
        order = await self.session.get(Order, order_id, with_for_update=for_update)
        if order is None:
            raise NotFoundError("Приказ не найден")
        return order

    async def save(self, data: OrderCreate, actor: UserRead, order_id: int | None = None) -> Order:
        require_role(actor, MANAGERS)
        order = await self.get_by_id(order_id, for_update=True) if order_id else Order()
        if order_id and not order.draft:
            raise ConflictError("Опубликованный приказ нельзя изменить")
        period = (
            await self.session.get(TestingPeriod, data.period_id, with_for_update=not data.draft)
            if data.period_id
            else None
        )
        if period is None and data.period_id:
            raise NotFoundError("TestingPeriod not found")
        if not data.draft:
            paper_required = self.validate_publication(data, period)
            data.details["paperReportsRequired"] = str(paper_required).lower()
            if period is not None:
                for key in ("surveyStartDate", "surveyEndDate", "surveySummaryDate"):
                    data.details.pop(key, None)
                if period.paper_reports_required != paper_required:
                    period.paper_reports_required = paper_required
                    await ReportService(self.session).refresh_period_completion(period)
        if data.details.get("paperReportsRequired") == "false":
            data.details.pop("paperReportDeadline", None)
        for key, value in data.model_dump(mode="json").items():
            setattr(order, key, value)
        self.session.add(order)
        await self.session.flush()
        audit(self.session, actor, "order.save", order.id)
        await self.session.commit()
        return order

    @staticmethod
    def validate_publication(data: OrderCreate, period: TestingPeriod | None) -> bool:
        if not data.number or not data.number.strip() or period is None:
            raise ValidationError("Для публикации укажите номер приказа и проверяемый период")
        if data.year != period.academic_year or data.semester != (
            "Осень" if period.semester == 1 else "Весна"
        ):
            raise ValidationError("Учебный год и семестр должны соответствовать выбранному периоду")
        setting = data.details.get(
            "paperReportsRequired", str(period.paper_reports_required).lower()
        )
        if setting not in {"true", "false"}:
            raise ValidationError("Укажите, требуется ли сдача бумажных отчётов")
        paper_required = setting == "true"
        try:
            fields = OrderPublication.model_validate(
                {
                    **data.details,
                    "paperReportDeadline": (
                        data.details.get("paperReportDeadline") if paper_required else None
                    ),
                }
            )
        except SchemaValidationError as error:
            names = ", ".join(str(item["loc"][0]) for item in error.errors())
            raise ValidationError(
                f"Заполните корректно обязательные поля приказа: {names}"
            ) from error
        if paper_required and fields.paperReportDeadline is None:
            raise ValidationError("Укажите срок сдачи бумажных отчётов")
        if not (
            data.date
            <= fields.preparationStartDate
            <= fields.preparationEndDate
            <= fields.testingStartDate
            <= fields.testingEndDate
            <= fields.resultsProcessingStartDate
            <= fields.checkSummaryDate
        ):
            raise ValidationError(
                "Проверьте последовательность подготовки, тестирования и обработки результатов"
            )
        return paper_required

    async def document(self, order_id: int, actor: UserRead) -> bytes:
        require_role(actor, MANAGERS)
        order = await self.get_by_id(order_id)
        if order.draft:
            raise ConflictError("Сначала сформируйте приказ из черновика")
        try:
            OrderPublication.model_validate(order.details)
        except SchemaValidationError as error:
            raise ConflictError(
                "В старом приказе недостаточно данных для печатной формы"
            ) from error
        from starlette.concurrency import run_in_threadpool

        from app.modules.orders.documents import order_pdf

        return await run_in_threadpool(order_pdf, order)

    async def delete(self, order_id: int, actor: UserRead) -> None:
        require_role(actor, MANAGERS)
        order = await self.get_by_id(order_id, for_update=True)
        if not order.draft:
            raise ConflictError("Можно удалить только черновик приказа")
        await self.session.delete(order)
        audit(self.session, actor, "order.delete", order_id)
        await self.session.commit()
