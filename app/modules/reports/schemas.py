from pydantic import BaseModel, ConfigDict, Field


class ReviewSave(BaseModel):
    approved: bool
    comment: str | None = Field(default=None, max_length=10000)


class ReportCreate(BaseModel):
    knowledge_test_id: int = Field(gt=0)
    electronic_file_key: str | None = Field(default=None, max_length=500)
    electronic_status: str | None = Field(default=None, max_length=32)
    electronic_comment: str | None = None
    paper_status: str | None = Field(default=None, max_length=32)
    paper_comment: str | None = None
    final_status: str | None = Field(default=None, max_length=32)


class ReportRead(ReportCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    previous_teacher_name: str | None = None


class ReportMetadata(BaseModel):
    previous_teacher_name: str | None = Field(default=None, max_length=255)


class ReportStatistics(BaseModel):
    """Report counters returned by the dashboard aggregation contract."""

    electronic_submitted: int | None = None
    electronic_with_issues: int | None = None
    paper_submitted: int | None = None
    paper_with_issues: int | None = None


class ReportOverview(BaseModel):
    knowledge_test_id: int
    report_id: int | None
    period_id: int
    period_name: str
    group_id: int
    group_name: str
    faculty_id: int | None
    faculty_name: str | None
    department_id: int | None
    department_name: str | None
    discipline_id: int
    discipline_name: str
    teacher_name: str | None
    previous_teacher_name: str | None = None
    electronic_status: str
    electronic_comment: str | None
    paper_status: str
    paper_comment: str | None
    paper_reports_required: bool
    final_status: str
    has_file: bool
    total_students: int
    participated_students: int
    participation_percentage: float
    at_least_half_participated: bool
