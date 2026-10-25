from pydantic import ValidationError as SchemaValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.permissions import MANAGERS, audit, require_role
from app.modules.orders.models import Order
from app.modules.orders.schemas import OrderCreate, OrderPublication
from app.modules.periods.service import PeriodService
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

    async def get_by_id(self, order_id: int) -> Order:
        order = await self.session.get(Order, order_id)
        if order is None:
            raise NotFoundError("Приказ не найден")
        return order

    async def save(self, data: OrderCreate, actor: UserRead, order_id: int | None = None) -> Order:
        require_role(actor, MANAGERS)
        order = await self.get_by_id(order_id) if order_id else Order()
        if order_id and not order.draft:
            raise ConflictError("Опубликованный приказ нельзя изменить")
        period = (
            await PeriodService(self.session).get_by_id(data.period_id) if data.period_id else None
        )
        if not data.draft:
            self.validate_publication(data, period)
            # Freeze the policy used in the issued document, even if the period changes later.
            data.details["paperReportsRequired"] = str(period.paper_reports_required).lower()
        for key, value in data.model_dump(mode="json").items():
            setattr(order, key, value)
        self.session.add(order)
        await self.session.flush()
        audit(self.session, actor, "order.save", order.id)
        await self.session.commit()
        return order

    @staticmethod
    def validate_publication(data: OrderCreate, period) -> None:
        if not data.number or not data.number.strip() or period is None:
            raise ValidationError("Для публикации укажите номер приказа и проверяемый период")
        if data.year != period.academic_year or data.semester != (
            "Осень" if period.semester == 1 else "Весна"
        ):
            raise ValidationError("Учебный год и семестр должны соответствовать выбранному периоду")
        try:
            fields = OrderPublication.model_validate(data.details)
        except SchemaValidationError as error:
            names = ", ".join(str(item["loc"][0]) for item in error.errors())
            raise ValidationError(
                f"Заполните корректно обязательные поля приказа: {names}"
            ) from error
        if period.paper_reports_required and fields.paperReportDeadline is None:
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
        if not fields.surveyStartDate <= fields.surveyEndDate <= fields.surveySummaryDate:
            raise ValidationError("Проверьте даты анкетирования и сводного отчёта по нему")

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
        order = await self.get_by_id(order_id)
        if not order.draft:
            raise ConflictError("Можно удалить только черновик приказа")
        await self.session.delete(order)
        audit(self.session, actor, "order.delete", order_id)
        await self.session.commit()
