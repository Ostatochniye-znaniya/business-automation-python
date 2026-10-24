"""Order and its two appendices, based on KnowledgeApp develop's printed form."""

import io
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from app.modules.reports.documents import pdf_font, report_flowables


def order_pdf(order) -> bytes:
    fields = order.details
    paper = fields.get("paperReportsRequired") == "true"

    def day(key):
        return date.fromisoformat(fields[key]).strftime("%d.%m.%Y")

    style = ParagraphStyle(
        "Order",
        fontName=pdf_font(),
        fontSize=12,
        leading=16,
        spaceAfter=9,
        firstLineIndent=25,
        alignment=4,
    )
    center = ParagraphStyle("Center", parent=style, alignment=1, firstLineIndent=0)

    def paragraph(text, centered=False):
        return Paragraph(escape(text).replace("\n", "<br/>"), center if centered else style)

    # Python periods use 1=autumn, 2=spring; the C# numeric convention differs.
    start_year = int(order.year[:4])
    previous_semester = "весеннем" if order.semester == "Осень" else "осеннем"
    previous_year = f"{start_year - 1}/{start_year}" if order.semester == "Осень" else order.year
    deadline = f"в электронном виде до {day('electronicReportDeadline')}"
    if paper:
        deadline += f", в бумажном виде до {day('paperReportDeadline')}"
    story = [
        paragraph("МИНИСТЕРСТВО НАУКИ И ВЫСШЕГО ОБРАЗОВАНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ", True),
        paragraph(
            "Федеральное государственное автономное образовательное учреждение высшего образования",
            True,
        ),
        paragraph("«МОСКОВСКИЙ ПОЛИТЕХНИЧЕСКИЙ УНИВЕРСИТЕТ»\n(МОСКОВСКИЙ ПОЛИТЕХ)", True),
        Spacer(1, 12),
        paragraph("ПРИКАЗ", True),
        paragraph(
            f"{date.fromisoformat(order.date).strftime('%d.%m.%Y')}    № {order.number}", True
        ),
        paragraph(order.title),
        paragraph(
            "В целях оценки качества подготовки обучающихся в соответствии с Положением о внутренней системе оценки качества образовательной деятельности и подготовке обучающихся по основным образовательным программам высшего образования в Московском политехническом университете и его филиалах, утвержденным приказом от 15.10.2022 № 1058-ОД"
        ),
        paragraph("ПРИКАЗЫВАЮ:"),
        paragraph(
            f"1. Провести проверку остаточных знаний обучающихся в форме тестирования по дисциплинам, освоенным в {previous_semester} семестре {previous_year} учебного года, в период с {day('testingStartDate')} по {day('testingEndDate')}."
        ),
        paragraph(
            "2. Утвердить рекомендации по организации и проведению проверки остаточных знаний обучающихся Университета (Приложение № 1)."
        ),
        paragraph(
            f"3. Деканам факультетов / директорам институтов организовать и провести проверку в соответствии с рекомендациями и представить отчеты о проверке остаточных знаний {deadline} в отдел контроля образовательного процесса (Приложение № 2)."
        ),
        paragraph(
            f"4. Начальник отдела контроля образовательного процесса {fields['bossControl']} обеспечивает методическое сопровождение сотрудников факультетов и институтов, ответственных за организацию и проведение проверки."
        ),
        paragraph(
            f"5. Контроль за исполнением приказа осуществляет начальник центра по учебно-методической работе {fields['bossMethod']}."
        ),
        Spacer(1, 20),
        paragraph("Проректор по учебной работе __________________ Г.Х. Шарипзянова"),
        PageBreak(),
    ]
    stamp = f"к приказу Московского Политеха от {date.fromisoformat(order.date).strftime('%d.%m.%Y')} № {order.number}"
    story += [
        paragraph(f"Приложение № 1\n{stamp}", True),
        paragraph(
            "Рекомендации по организации и проведению проверки остаточных знаний обучающихся Университета",
            True,
        ),
    ]
    first_course = "2" if order.semester == "Осень" else "1"
    recommendations = [
        f"1. Проверка проводится в три этапа: подготовительный (подготовка тестовых материалов, формирование списков студентов и графиков тестирования) с {day('preparationStartDate')} по {day('preparationEndDate')}; тестирование с {day('testingStartDate')} по {day('testingEndDate')}; обработка и анализ результатов, формирование отчета с {day('resultsProcessingStartDate')} по {day('checkSummaryDate')}.",
        f"2. Проверка проводится в отношении учебных групп {first_course}-3 курсов очной формы обучения бакалавриата, {first_course}-4 курсов специалитета и 1 курса магистратуры.",
        "3. Учебные группы отбираются по принципу представительства одной группы от одного профиля/специализации.",
        f"4. Для каждой группы определяются две дисциплины, изученные в {previous_semester} семестре {previous_year} учебного года.",
        "5. При отборе дисциплин учитываются универсальные (для 1 курса), общепрофессиональные и профессиональные компетенции. В перечень включаются дисциплины штатных преподавателей, у которых заканчивается срок трудового договора в августе, и не менее одной дисциплины выпускающей кафедры, ответственной за группу и профиль/специализацию.",
        "6. Расписание по группам и аудиториям согласовывается с расписанием учебных занятий, готовится и утверждается факультетами/институтами.",
        "7. В тестировании должны принять участие не менее 50% студентов.",
        "8. Тестирование, обработка и анализ результатов, формирование отчетов проводятся ответственными лицами, назначенными деканами факультетов/директорами институтов.",
        f"9. Отчеты представляются в отдел контроля образовательного процесса {deadline}.",
        f"10. Анкетирование проводится с {day('surveyStartDate')} по {day('surveyEndDate')}; сводный отчет по анкетированию представляется до {day('surveySummaryDate')}.",
    ]
    story.extend(paragraph(text) for text in recommendations)
    story += [PageBreak(), paragraph(f"Приложение № 2\n{stamp}", True), Spacer(1, 12)]
    story += report_flowables(
        {"academic_year": order.year, "blank": True},
        [{"student": "", "participation_status": ""} for _ in range(5)],
        template=True,
    )
    buffer = io.BytesIO()
    SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=65, rightMargin=45, topMargin=45, bottomMargin=45
    ).build(story)
    return buffer.getvalue()
