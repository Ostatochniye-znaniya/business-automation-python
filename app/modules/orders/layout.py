"""Typography and printable form geometry from the university's reference order."""

import os
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

PAGE_WIDTH, PAGE_HEIGHT = A4
# The reference images are cropped pages, not edge-to-edge A4 print areas.
# Report geometry comes from reports/templates/group_report.docx (twips / 20).
LEFT = 85.05
RIGHT = 28.35
WIDTH = PAGE_WIDTH - LEFT - RIGHT
REPORT_COLUMNS = (32.35, 196.05, 119.7, 118.15)
REPORT_WIDTH = sum(REPORT_COLUMNS)
SIGNATURE_COLUMNS = (280.55, 74.8, 111.9)
CELL_INSET = 5.4
FIRST_LINE = 35.45
STAMP_LEFT = PAGE_WIDTH / 2
FOOTER_TOP = 85.05
FONT = "OrderSerif"
MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def register_fonts() -> None:
    """Embed a complete serif family; Liberation matches Times metrics on Linux."""
    if FONT in pdfmetrics.getRegisteredFontNames():
        return
    times_windows = ["times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"]
    times_macos = [
        f"Times New Roman{suffix}.ttf" for suffix in ["", " Bold", " Italic", " Bold Italic"]
    ]
    families = [
        (Path("C:/Windows/Fonts"), times_windows),
        (Path("/System/Library/Fonts/Supplemental"), times_macos),
        *[
            (
                Path(f"/usr/share/fonts/truetype/{directory}"),
                [
                    f"LiberationSerif-{suffix}.ttf"
                    for suffix in ["Regular", "Bold", "Italic", "BoldItalic"]
                ],
            )
            for directory in ["liberation", "liberation2"]
        ],
    ]
    if directory := os.environ.get("ORDER_FONT_DIR"):
        # An explicit reference font must never silently fall back to a substitute.
        families = [(Path(directory), names) for names in [times_windows, times_macos]]
    for directory, names in families:
        if all((directory / name).is_file() for name in names):
            for suffix, filename in zip(
                ["", "-Bold", "-Italic", "-BoldItalic"], names, strict=True
            ):
                pdfmetrics.registerFont(TTFont(FONT + suffix, str(directory / filename)))
            pdfmetrics.registerFontFamily(
                FONT,
                normal=FONT,
                bold=FONT + "-Bold",
                italic=FONT + "-Italic",
                boldItalic=FONT + "-BoldItalic",
            )
            return
    raise RuntimeError(
        "Для приказа установите Times New Roman или Liberation Serif (все начертания); "
        "если задан ORDER_FONT_DIR, он должен содержать все четыре файла Times New Roman"
    )


def paragraph(text: str, kind: str = "body") -> Paragraph:
    """Escape variable data and apply only the formatting appropriate to its role."""
    options = {
        "body": {"alignment": TA_JUSTIFY, "firstLineIndent": FIRST_LINE},
        "left": {},
        "position": {"alignment": TA_JUSTIFY, "justifyBreaks": 1},
        "right": {"alignment": TA_RIGHT},
        "center": {"alignment": TA_CENTER},
        "heading": {"alignment": TA_CENTER, "fontName": FONT + "-Bold"},
        "command": {"firstLineIndent": FIRST_LINE, "fontName": FONT + "-Bold"},
        "ministry": {"alignment": TA_CENTER, "fontSize": 10, "leading": 14},
        "institution": {"alignment": TA_CENTER, "fontSize": 8.5, "leading": 14},
        "university": {"alignment": TA_CENTER, "fontName": FONT + "-Bold", "fontSize": 12},
        "order": {
            "alignment": TA_CENTER,
            "fontName": FONT + "-Bold",
            "fontSize": 22,
            "leading": 26,
        },
        "table": {"fontSize": 12, "leading": 13.8},
        "label": {"fontName": FONT + "-Bold", "fontSize": 12, "leading": 13.8},
        "column": {
            "alignment": TA_CENTER,
            "fontName": FONT + "-Bold",
            "fontSize": 12,
            "leading": 13.8,
        },
        "caption": {
            "alignment": TA_CENTER,
            "fontName": FONT + "-Italic",
            "fontSize": 8,
            "leading": 10,
        },
        "footer": {"fontSize": 9, "leading": 10},
    }
    style = ParagraphStyle(
        kind,
        **({"fontName": FONT, "fontSize": 14, "leading": 16, "alignment": TA_LEFT} | options[kind]),
    )
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def borderless_table(data: list, widths: list[float]) -> Table:
    """Align independent requisites without space characters or paragraph indents."""
    table = Table(data, colWidths=widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def requisites(order_date, number: str) -> Table:
    """Put the date at the left and the underlined order number at the right."""
    number_width = max(105, min(WIDTH / 2, pdfmetrics.stringWidth(number, FONT, 14) + 16))
    table = borderless_table(
        [
            [
                paragraph(order_date.strftime("%d.%m.%Y"), "center"),
                "",
                paragraph("№", "left"),
                paragraph(number, "center"),
            ]
        ],
        [105, WIDTH - 125 - number_width, 20, number_width],
    )
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (0, 0), 0.5, colors.black),
                ("LINEBELOW", (3, 0), (3, 0), 0.5, colors.black),
            ]
        )
    )
    return table


def appendix_stamp(index: int, order_date, number: str) -> Table:
    """Use the right-hand three-line appendix stamp, keeping its text left-aligned."""
    stamp = paragraph(f"Приложение № {index}\nк приказу Московского Политеха", "left")
    stamp_width = PAGE_WIDTH - RIGHT - STAMP_LEFT
    stamp_date = borderless_table(
        [
            [
                paragraph("от «", "left"),
                paragraph(f"{order_date.day:02}", "center"),
                paragraph("»", "left"),
                paragraph(MONTHS[order_date.month - 1], "center"),
                paragraph(f"{order_date.year} г. №", "center"),
                paragraph(number, "center"),
            ]
        ],
        [26, 28, 10, 76, 62, stamp_width - 202],
    )
    stamp_date.setStyle(
        TableStyle(
            [("LINEBELOW", (column, 0), (column, 0), 0.5, colors.black) for column in [1, 3, 5]]
        )
    )
    return borderless_table([["", [stamp, stamp_date]]], [STAMP_LEFT - LEFT, stamp_width])


def report_form(academic_year: str) -> list:
    """Reproduce appendix 2, including merged cells, empty totals and signatures."""
    labels = [
        f"Учебный год: {academic_year}",
        "Код и наименование направления (специальности):",
        "Наименование образовательной программы:",
        "Наименование дисциплины:",
        "ФИО педагогического работника, проводившего занятия в предыдущем\nсеместре:",
        "Учебная группа №",
    ]
    data = [
        [paragraph("№", "column") if i == 0 else "", paragraph(label, "label"), "", ""]
        for i, label in enumerate(labels)
    ]
    data.append(
        [
            "",
            *[
                paragraph(label, "column")
                for label in [
                    "ФИО обучающегося",
                    "Результаты промежуточной аттестации",
                    "Результаты тестирования",
                ]
            ],
        ]
    )
    data.extend([[paragraph(number, "table"), "", "", ""] for number in ["1", "2", "3", "…", "n"]])
    data.extend(
        [
            [paragraph(f"{label}:{chr(160) * spaces}(чел.)", "table"), "", "", ""]
            for label, spaces in [
                ("Всего в группе", 9),
                ("Прошли тестирование", 10),
                ("Не допущены к тестированию", 10),
                ("Не явилось на тестирование", 10),
            ]
        ]
    )
    table = Table(
        data,
        colWidths=REPORT_COLUMNS,
        rowHeights=[15.3, 29.1, 29.1, 29.1, 29.1, 15.3, 42.9, *[15.3] * 9],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BOX", (0, 0), (-1, -1), 1.5, colors.black),
                ("SPAN", (0, 0), (0, 6)),
                *[("SPAN", (1, i), (3, i)) for i in range(6)],
                *[("SPAN", (0, i), (3, i)) for i in range(12, 16)],
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), CELL_INSET),
                ("RIGHTPADDING", (0, 0), (-1, -1), CELL_INSET),
                ("TOPPADDING", (0, 0), (-1, -1), 0.75),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0.75),
            ]
        )
    )
    result = [
        paragraph("Отчет о проверке остаточных знаний", "heading"),
        Spacer(1, 26),
        table,
        Spacer(1, 17),
    ]
    for label in ["Заведующий кафедрой", "Декан факультета/Директор института"]:
        description = (
            " <i>(наименование<br/>полностью)</i>"
            if label == "Заведующий кафедрой"
            else "<br/><i>(наименование полностью)</i>"
        )
        position = Paragraph(escape(label) + description, paragraph("", "position").style)
        caption = borderless_table(
            [[paragraph("подпись", "caption")]], [SIGNATURE_COLUMNS[1] - CELL_INSET * 2]
        )
        caption.setStyle(
            TableStyle(
                [
                    ("LINEABOVE", (0, 0), (0, 0), 0.5, colors.black),
                    ("TOPPADDING", (0, 0), (0, 0), 2),
                ]
            )
        )
        signature = [Spacer(1, 36), caption]
        signatures = borderless_table(
            [[position, signature, [Spacer(1, 16), paragraph("ФИО", "left")]]],
            SIGNATURE_COLUMNS,
        )
        signatures.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), CELL_INSET),
                    ("RIGHTPADDING", (0, 0), (-1, -1), CELL_INSET),
                ]
            )
        )
        result.extend([signatures, Spacer(1, 2)])
    return result
