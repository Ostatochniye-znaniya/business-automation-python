"""Printable forms populated from persisted domain data."""

import csv
import io
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Cm, Pt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def report_docx(context: dict, rows: list[dict]) -> bytes:
    document = Document()
    document.styles["Normal"].font.name = "Times New Roman"
    document.styles["Normal"].font.size = Pt(11)
    section = document.sections[0]
    section.left_margin = section.right_margin = Cm(1.8)
    document.add_heading("Отчёт о проверке остаточных знаний", 0)
    for label, key in [
        ("Учебный год", "academic_year"),
        ("Направление подготовки", "program"),
        ("Наименование дисциплины", "discipline"),
        ("Учебная группа", "group"),
        ("Преподаватель, проводивший проверку", "teacher"),
    ]:
        document.add_paragraph(f"{label}: {context.get(key) or '________________'}")
    document.add_paragraph(
        "ФИО педагогического работника, проводившего занятия в предыдущем семестре: "
        + (context.get("previous_teacher") or "__________________")
    )
    table = document.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    for cell, value in zip(
        table.rows[0].cells,
        ["№", "ФИО обучающегося", "Результаты промежуточной аттестации", "Результаты тестирования"],
        strict=True,
    ):
        cell.text = value
    status_labels = {"ABSENT": "Не явился", "NOT_ADMITTED": "Не допущен"}
    for index, row in enumerate(rows, 1):
        values = [
            str(index),
            row["student"],
            str(
                row.get("intermediate_result") if row.get("intermediate_result") is not None else ""
            ),
            status_labels.get(row["participation_status"], str(row.get("testing_result", ""))),
        ]
        for cell, value in zip(table.add_row().cells, values, strict=True):
            cell.text = value
    document.add_paragraph(f"Всего в группе: {len(rows)} чел.")
    for code, text in [
        ("PASSED", "Прошли тестирование"),
        ("NOT_ADMITTED", "Не допущены"),
        ("ABSENT", "Не явились"),
    ]:
        document.add_paragraph(
            f"{text}: {sum(row['participation_status'] == code for row in rows)} чел."
        )
    document.add_paragraph(
        f"Заведующий кафедрой {context.get('department', '')} __________________ / {context.get('chair_head', '__________________')}"
    )
    document.add_paragraph(
        f"Декан факультета / Директор института __________________ / {context.get('faculty_head', '__________________')}"
    )
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def schedule_pdf(title: str, rows: list[list[str]], signatory: str) -> bytes:
    font_paths = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    font_path = next((path for path in font_paths if path.is_file()), None)
    if font_path is None:
        raise RuntimeError("Для PDF установите шрифт DejaVu Sans")
    if "ScheduleFont" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ScheduleFont", str(font_path)))
    style = ParagraphStyle("Schedule", fontName="ScheduleFont", fontSize=8, leading=11)
    header = [
        "№",
        "Группа",
        "Профиль подготовки",
        "Дисциплина",
        "Кафедра",
        "ФИО ППС",
        "Дата / время (Москва)",
        "Место",
    ]
    data = [[Paragraph(escape(str(cell)), style) for cell in row] for row in [header, *rows]]
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=25, bottomMargin=25
    )
    table = Table(data, repeatRows=1, colWidths=[25, 55, 115, 135, 100, 110, 90, 65])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    doc.build(
        [
            Paragraph(escape(title), style),
            Spacer(1, 12),
            table,
            Spacer(1, 24),
            Paragraph(escape(signatory), style),
        ]
    )
    return buffer.getvalue()


def csv_bytes(headers: list[str], rows: list[list]) -> bytes:
    def safe(value):
        text = str(value if value is not None else "")
        return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text

    stream = io.StringIO()
    writer = csv.writer(stream, delimiter=";")
    writer.writerow(headers)
    writer.writerows([[safe(value) for value in row] for row in rows])
    return stream.getvalue().encode("utf-8-sig")
