from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.permissions import MANAGERS, audit, require_role
from app.modules.departments.models import Department
from app.modules.departments.schemas import DepartmentCreate, DepartmentRead
from app.modules.departments.service import DepartmentService
from app.modules.disciplines.models import Discipline
from app.modules.groups.models import StudyGroup, StudyProgram
from app.modules.users.models import User
from app.modules.users.schemas import UserRead


async def tree(session: AsyncSession, actor: UserRead):
    require_role(actor, MANAGERS)
    counts = dict(
        (
            await session.execute(
                select(User.department_id, func.count(User.id)).group_by(User.department_id)
            )
        ).all()
    )
    departments = (await session.scalars(select(Department).order_by(Department.name))).all()
    return [
        {**DepartmentRead.model_validate(d).model_dump(), "employee_count": counts.get(d.id, 0)}
        for d in departments
    ]


async def save_department(data, session, actor, department_id=None):
    require_role(actor, MANAGERS)
    service = DepartmentService(session)
    entity = await service.get_by_id(department_id) if department_id else Department()
    if data.parent_id:
        await service.get_by_id(data.parent_id)
        if department_id and data.parent_id in await service.subtree_ids(department_id):
            raise ValidationError("Подразделение нельзя переместить в собственное поддерево")
    for key, value in data.model_dump().items():
        setattr(entity, key, value)
    session.add(entity)
    await session.flush()
    audit(session, actor, "department.save", entity.id)
    await session.commit()
    return entity


async def create(data: DepartmentCreate, session: AsyncSession, actor: UserRead):
    return await save_department(data, session, actor)


async def update(
    department_id: int, data: DepartmentCreate, session: AsyncSession, actor: UserRead
):
    return await save_department(data, session, actor, department_id)


async def delete(department_id: int, session: AsyncSession, actor: UserRead):
    require_role(actor, MANAGERS)
    department = await session.get(Department, department_id)
    if department is None:
        raise NotFoundError("Подразделение не найдено")
    for model, field in [
        (Department, Department.parent_id),
        (User, User.department_id),
        (StudyGroup, StudyGroup.department_id),
        (Discipline, Discipline.department_id),
        (StudyProgram, StudyProgram.faculty_id),
    ]:
        if await session.scalar(select(model.id).where(field == department_id).limit(1)):
            raise ConflictError(
                "Сначала переназначьте сотрудников, группы и дочерние подразделения"
            )
    audit(session, actor, "department.delete", department_id)
    await session.delete(department)
    await session.commit()
