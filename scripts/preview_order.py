"""Generate an isolated order preview without a database, login or publication."""

import argparse
import json
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

from app.modules.orders.documents import order_pdf


def main() -> None:
    """Save a reference-data PDF and, optionally, full A4 page images for comparison."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, help="Order object saved as JSON; otherwise use reference dates"
    )
    parser.add_argument("--output", type=Path, default=Path(".qa/order-layout"))
    parser.add_argument("--png", action="store_true", help="Also render pages; requires pypdfium2")
    args = parser.parse_args()
    values = {
        "title": "О проведении проверки остаточных знаний обучающихся",
        "number": "1218-ОД",
        "year": "2025/2026",
        "semester": "Осень",
        "date": "2025-10-16",
        "details": {
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
    }
    if args.input:
        values = json.loads(args.input.read_text(encoding="utf-8"))
    data = order_pdf(SimpleNamespace(**values))
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / "order.pdf"
    target.write_bytes(data)
    print(target.resolve())
    if args.png:
        try:
            import pypdfium2
        except ImportError:
            parser.error("Для PNG установите pypdfium2: python -m pip install pypdfium2")
        with pypdfium2.PdfDocument(data) as document:
            for index in range(len(document)):
                with closing(document[index]) as page, closing(page.render(scale=2)) as bitmap:
                    image = args.output / f"page-{index + 1}.png"
                    bitmap.to_pil().save(image)
                    print(image.resolve())


if __name__ == "__main__":
    main()
