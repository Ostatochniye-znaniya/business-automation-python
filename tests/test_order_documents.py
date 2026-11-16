"""Check the actual PDF's page geometry, typography and variable requisites."""

import io
from types import SimpleNamespace

import pytest
from docx import Document
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4

from app.modules.orders.documents import order_pdf
from app.modules.orders.layout import (
    CELL_INSET,
    FIRST_LINE,
    LEFT,
    REPORT_COLUMNS,
    REPORT_WIDTH,
    SIGNATURE_COLUMNS,
    STAMP_LEFT,
    register_fonts,
    report_form,
)
from app.modules.reports.documents import TEMPLATE


def make_order(**updates):
    """Use the reference dates with the application's additional survey fields."""
    values = dict(
        title="О проведении проверки остаточных знаний обучающихся",
        number="1218-ОД",
        year="2025/2026",
        semester="Осень",
        date="2025-10-16",
        details={
            "bossControl": "Е.В. Давыдова",
            "bossMethod": "Т.С. Леухина",
            "paperReportsRequired": "true",
            "preparationStartDate": "2025-10-20",
            "preparationEndDate": "2025-10-24",
            "testingStartDate": "2025-10-27",
            "testingEndDate": "2025-12-12",
            "electronicReportDeadline": "2025-12-12",
            "paperReportDeadline": "2025-12-12",
            "resultsProcessingStartDate": "2025-12-15",
            "checkSummaryDate": "2026-01-30",
            "surveyStartDate": "2025-12-15",
            "surveyEndDate": "2025-12-19",
            "surveySummaryDate": "2026-01-30",
        },
    )
    return SimpleNamespace(**(values | updates))


def text_positions(page):
    """Resolve text transforms to page coordinates, including paragraphs in tables."""
    positions = []

    def visit(text, cm, tm, font, size):
        """Retain font and baseline data for non-empty text fragments."""
        if text.strip():
            positions.append(
                dict(
                    text=text.strip(),
                    x=tm[4] * cm[0] + tm[5] * cm[2] + cm[4],
                    y=tm[4] * cm[1] + tm[5] * cm[3] + cm[5],
                    size=size,
                    font=str(font.get("/BaseFont", "")),
                )
            )

    page.extract_text(visitor_text=visit)
    return positions


def test_order_has_three_pages_and_separate_appendices():
    """The reference-size document must not spill into extra pages."""
    pdf = PdfReader(io.BytesIO(order_pdf(make_order())))
    assert len(pdf.pages) == 3
    for index, page in enumerate(pdf.pages):
        assert float(page.mediabox.width) == pytest.approx(A4[0], abs=0.01)
        assert float(page.mediabox.height) == pytest.approx(A4[1], abs=0.01)
        text = page.extract_text()
        assert "Исп.: Е.В. Давыдова" in text
        assert "3364791" not in text
        assert "Сертификат" not in text
        if index:
            assert f"Приложение № {index}" in text
            assert "16" in text and "октября" in text and "1218-ОД" in text
    assert "ПРИКАЗЫВАЮ:" in pdf.pages[0].extract_text()
    assert "Рекомендации по организации" in pdf.pages[1].extract_text()
    assert "Отчет о проверке" in pdf.pages[2].extract_text()


def test_date_number_title_and_appendix_stamps_have_reference_alignment():
    """Catch the old centered requisites and indented subject regression."""
    pdf = PdfReader(io.BytesIO(order_pdf(make_order())))
    first = text_positions(pdf.pages[0])
    date = next(item for item in first if item["text"] == "16.10.2025")
    number = next(item for item in first if item["text"] == "1218-ОД")
    assert date["x"] < A4[0] / 4
    assert number["x"] > A4[0] * 0.75
    assert date["y"] == pytest.approx(number["y"])
    subject = next(item for item in first if item["text"] == "О проведении проверки")
    assert subject["x"] == pytest.approx(LEFT)
    body = next(item for item in first if item["text"].startswith("В целях"))
    assert body["x"] == pytest.approx(LEFT + FIRST_LINE)
    command = next(item for item in first if item["text"] == "ПРИКАЗЫВАЮ:")
    assert "Bold" in command["font"]
    for index in [1, 2]:
        stamp = next(
            item
            for item in text_positions(pdf.pages[index])
            if item["text"] == f"Приложение № {index}"
        )
        assert stamp["x"] == pytest.approx(STAMP_LEFT)


def test_appendix_table_and_signatures_preserve_the_reference_structure():
    """The number cell spans metadata and column headings; totals remain blank."""
    register_fonts()
    flowables = report_form("2025/2026")
    table = flowables[2]
    assert ("SPAN", (0, 0), (0, 6)) in table._spanCmds
    assert len(table._cellvalues) == 16
    assert sum(table._argW) == pytest.approx(REPORT_WIDTH)
    assert table._cellvalues[7][0].getPlainText() == "1"
    assert table._cellvalues[11][0].getPlainText() == "n"
    assert "5" not in table._cellvalues[12][0].getPlainText()
    pdf = PdfReader(io.BytesIO(order_pdf(make_order())))
    text = pdf.pages[2].extract_text()
    assert "Учебный год: 2025/2026" in text
    assert text.count("подпись") == 2
    assert text.count("ФИО") == 4


def test_report_dimensions_and_type_sizes_match_the_original_docx():
    """Use an independent source, so a self-consistent but too-wide PDF fails."""
    source = Document(TEMPLATE)
    assert LEFT == pytest.approx(source.sections[0].left_margin.pt)
    assert REPORT_COLUMNS == pytest.approx([column.width.pt for column in source.tables[0].columns])
    assert SIGNATURE_COLUMNS == pytest.approx(
        [column.width.pt for column in source.tables[1].columns]
    )
    table_style = source.tables[0].style
    assert table_style.font.name == "Times New Roman"
    assert table_style.font.size.pt == 12
    pdf = PdfReader(io.BytesIO(order_pdf(make_order())))
    positions = text_positions(pdf.pages[2])
    year = next(item for item in positions if item["text"].startswith("Учебный год:"))
    assert year["x"] == pytest.approx(122.8, abs=0.01)
    assert year["size"] == table_style.font.size.pt
    assert "Bold" in year["font"]
    heading = next(item for item in positions if item["text"] == source.paragraphs[0].text)
    assert heading["size"] == source.paragraphs[0].runs[0].font.size.pt
    name = next(item for item in positions if item["text"] == "ФИО")
    assert name["x"] == pytest.approx(445.8, abs=0.01)
    chair = next(item for item in positions if item["text"] == "Заведующий кафедрой")
    assert chair["x"] == pytest.approx(LEFT + CELL_INSET)
    assert chair["size"] == 14
    assert all(
        "TimesNewRoman" in item["font"] or "LiberationSerif" in item["font"] for item in positions
    )


def test_stamp_date_never_wraps_its_static_text_and_fonts_are_embedded():
    """Detect a split quote/date line and accidental fallback to Helvetica."""
    pdf = PdfReader(io.BytesIO(order_pdf(make_order())))
    for page in pdf.pages[1:]:
        positions = text_positions(page)
        date_fields = [
            next(item for item in positions if item["text"] == text)
            for text in ["от «", "16", "»", "октября", "2025 г. №", "1218-ОД"]
        ]
        assert len({round(item["y"], 2) for item in date_fields}) == 1
        assert next(item for item in positions if item["text"].startswith("О проведении"))["y"] > 70
        for font in page["/Resources"]["/Font"].values():
            font = font.get_object()
            if "/FontDescriptor" in font:
                assert "/FontFile2" in font["/FontDescriptor"]


def test_explicit_times_directory_does_not_silently_substitute_fonts(monkeypatch, tmp_path):
    """A missing reference font is an error, not an unnoticed change of typeface."""
    from app.modules.orders import layout

    monkeypatch.setenv("ORDER_FONT_DIR", str(tmp_path))
    monkeypatch.setattr(layout.pdfmetrics, "getRegisteredFontNames", lambda: [])
    with pytest.raises(RuntimeError, match="ORDER_FONT_DIR"):
        register_fonts()


@pytest.mark.parametrize("paper", [True, False])
@pytest.mark.parametrize("semester,previous", [("Осень", "весеннем"), ("Весна", "осеннем")])
def test_order_retains_period_dates_and_paper_policy(paper, semester, previous):
    """Layout changes must not replace user data with the example's fixed values."""
    order = make_order(number="42-ОД", date="2026-02-03", year="2026/2027", semester=semester)
    order.details["paperReportsRequired"] = str(paper).lower()
    order.details["electronicReportDeadline"] = "2026-05-20"
    order.details["bossControl"] = "Иванов И.И."
    if paper:
        order.details["paperReportDeadline"] = "2026-05-21"
    else:
        del order.details["paperReportDeadline"]
    pdf = PdfReader(io.BytesIO(order_pdf(order)))
    text = " ".join(page.extract_text() for page in pdf.pages)
    assert "42-ОД" in text and "1218-ОД" not in text
    assert "03.02.2026" in text and "февраля" in text
    assert previous in text
    assert "20.05.2026" in text
    assert ("21.05.2026" in text) is paper
    assert ("в бумажном виде" in text) is paper
    assert "Иванов И.И." in text
    assert "Анкетирование" in text and "19.12.2025" in text


def test_long_requisites_are_escaped_and_never_overlap_the_footer():
    """Exercise maximum-length input and safe pagination, not only the sample."""
    order = make_order(number="ДЛИННЫЙ-НОМЕР-" * 3, title="Проверка <знаний> & результатов " * 15)
    order.details["bossControl"] = "Начальник <отдела> & ответственный " * 5
    order.details["bossMethod"] = "Методист " * 20
    pdf = PdfReader(io.BytesIO(order_pdf(order)))
    text = " ".join(page.extract_text() for page in pdf.pages)
    assert "<знаний> & результатов" in text
    assert "<отдела> & ответственный" in text
    assert "ДЛИННЫЙ-НОМЕР" in text
    for page in pdf.pages:
        positions = text_positions(page)
        footer_top = max(item["y"] for item in positions if item["size"] == 9)
        for item in positions:
            assert item["x"] >= LEFT - 0.01
            assert item["y"] > 10
            if item["size"] != 9:
                assert item["y"] > footer_top + 10
