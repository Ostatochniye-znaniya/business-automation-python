"""Check the university form's structure and real values, including zero grades."""

import io
from zipfile import ZipFile

from docx import Document

from app.modules.reports.documents import TEMPLATE, report_docx


def test_filled_report_preserves_template_and_all_students():
    rows = [
        {
            "student": f"Студент {index:02}",
            "intermediate_result": 0,
            "testing_result": 0,
            "participation_status": "PASSED",
        }
        for index in range(42)
    ]
    rows[-1]["participation_status"] = "ABSENT"
    rows[-2]["participation_status"] = "NOT_ADMITTED"
    data = report_docx(
        {
            "academic_year": "2026/2027",
            "program_code": "09.03.01",
            "program_name": "Информатика",
            "discipline": "Базы данных",
            "group": "261-001",
            "previous_teacher": "Иванов И.И.",
        },
        rows,
    )
    document = Document(io.BytesIO(data))
    table = document.tables[0]
    assert len(table.rows) == 6 + 1 + 42 + 4
    assert table.rows[7].cells[2].text == "0"
    assert table.rows[7].cells[3].text == "0"
    assert table.rows[-5].cells[3].text == "Не явился"
    assert table.rows[-6].cells[3].text == "Не допущен"
    assert "40 (чел.)" in table.rows[-3].cells[0].text
    assert "Иванов И.И." in table.rows[4].cells[-1].text
    # Fonts, page setup and unrelated template parts must survive population.
    with ZipFile(TEMPLATE) as source, ZipFile(io.BytesIO(data)) as output:
        for name in source.namelist():
            if name not in {"word/document.xml", "docProps/core.xml"}:
                assert output.read(name) == source.read(name), name
