from pydantic import BaseModel, ConfigDict, Field


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
