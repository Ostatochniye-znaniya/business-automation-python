from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    LPR = "LPR"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD"
    DEPARTMENT_RESPONSIBLE = "DEPARTMENT_RESPONSIBLE"
    CHAIR_HEAD = "CHAIR_HEAD"
    TEACHER = "TEACHER"
    GUEST = "GUEST"


class DepartmentType(StrEnum):
    UNIVERSITY = "UNIVERSITY"
    INSTITUTE = "INSTITUTE"
    FACULTY = "FACULTY"
    DEPARTMENT = "DEPARTMENT"


class TestingPeriodStatus(StrEnum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ParticipationStatus(StrEnum):
    PASSED = "PASSED"
    ABSENT = "ABSENT"
    NOT_ADMITTED = "NOT_ADMITTED"
