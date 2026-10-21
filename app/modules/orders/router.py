from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.orders.schemas import OrderCreate, OrderRead
from app.modules.orders.service import OrderService
from app.modules.users.dependencies import get_current_user, require_staff
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/orders", tags=["orders"])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Actor = Annotated[UserRead, Depends(get_current_user)]


@router.get("", response_model=list[OrderRead], dependencies=[Depends(require_staff)])
async def list_orders(
    session: Session,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    return await OrderService(session).list_orders(offset, limit)


@router.post("", response_model=OrderRead, status_code=201)
async def create(data: OrderCreate, session: Session, actor: Actor):
    return await OrderService(session).save(data, actor)


@router.put("/{order_id}", response_model=OrderRead)
async def update(order_id: int, data: OrderCreate, session: Session, actor: Actor):
    return await OrderService(session).save(data, actor, order_id)


@router.delete("/{order_id}", status_code=204)
async def delete(order_id: int, session: Session, actor: Actor):
    await OrderService(session).delete(order_id, actor)
