from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import MANAGERS, audit, require_role
from app.modules.orders.models import Order
from app.modules.orders.schemas import OrderCreate
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
        if data.period_id:
            await PeriodService(self.session).get_by_id(data.period_id)
        for key, value in data.model_dump(mode="json").items():
            setattr(order, key, value)
        self.session.add(order)
        await self.session.flush()
        audit(self.session, actor, "order.save", order.id)
        await self.session.commit()
        return order

    async def delete(self, order_id: int, actor: UserRead) -> None:
        require_role(actor, MANAGERS)
        order = await self.get_by_id(order_id)
        if not order.draft:
            raise ConflictError("Можно удалить только черновик приказа")
        await self.session.delete(order)
        audit(self.session, actor, "order.delete", order_id)
        await self.session.commit()
