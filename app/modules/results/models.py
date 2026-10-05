from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ParticipationStatus
from app.db.base import Base


class TestResult(Base):
    __tablename__ = "test_results"
    __table_args__ = (
        UniqueConstraint("knowledge_test_id", "student_id", name="uq_result_test_student"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    knowledge_test_id: Mapped[int] = mapped_column(ForeignKey("knowledge_tests.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    intermediate_result: Mapped[float | None] = mapped_column()
    testing_result: Mapped[float | None] = mapped_column()
    participation_status: Mapped[ParticipationStatus] = mapped_column(Enum(ParticipationStatus))
