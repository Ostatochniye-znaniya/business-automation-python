"""Order and its appendices laid out according to the university's printed form."""

import io
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Spacer

from app.modules.orders.layout import (
    FONT,
    FOOTER_TOP,
    LEFT,
    PAGE_HEIGHT,
    WIDTH,
    appendix_stamp,
    borderless_table,
    paragraph,
    register_fonts,
    report_form,
    requisites,
)


def order_pdf(order) -> bytes:
    """Render saved order data without copying the reference's signature or document ID."""
    register_fonts()
    fields = order.details
    paper = fields.get("paperReportsRequired") == "true"
    order_date = date.fromisoformat(order.date)
    footer = paragraph(f"{order.title}\nИсп.: {fields['bossControl']}", "footer")
    _, footer_height = footer.wrap(WIDTH, PAGE_HEIGHT)
    footer_top = max(FOOTER_TOP, footer_height + 12)
    bottom = max(100, footer_top + 12)

    def day(key):
        """Format a persisted ISO date independently of the host locale."""
        return date.fromisoformat(fields[key]).strftime("%d.%m.%Y")

    def page_decoration(canvas, document):
        """Repeat the subject and executor in the footer; omit the first page number."""
        canvas.saveState()
        canvas.setFont(FONT, 10)
        if document.page > 1:
            canvas.drawCentredString(LEFT + WIDTH / 2, PAGE_HEIGHT - 18, str(document.page))
        footer.drawOn(canvas, LEFT, footer_top - footer_height)
        canvas.restoreState()

    # Python periods use 1=autumn, 2=spring; the C# numeric convention differs.
    start_year = int(order.year[:4])
    previous_semester = "весеннем" if order.semester == "Осень" else "осеннем"
    previous_year = f"{start_year - 1}/{start_year}" if order.semester == "Осень" else order.year
    deadline = f"в электронном виде до {day('electronicReportDeadline')}"
    if paper:
        deadline += f", в бумажном виде до {day('paperReportDeadline')}"
    title = order.title
    if title.strip() == "О проведении проверки остаточных знаний обучающихся":
        title = "О проведении проверки\nостаточных знаний обучающихся"
    story = [
        paragraph("МИНИСТЕРСТВО НАУКИ И ВЫСШЕГО ОБРАЗОВАНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ", "ministry"),
        paragraph(
            "ФЕДЕРАЛЬНОЕ ГОСУДАРСТВЕННОЕ АВТОНОМНОЕ ОБРАЗОВАТЕЛЬНОЕ УЧРЕЖДЕНИЕ ВЫСШЕГО ОБРАЗОВАНИЯ",
            "institution",
        ),
        paragraph("«МОСКОВСКИЙ ПОЛИТЕХНИЧЕСКИЙ УНИВЕРСИТЕТ»", "university"),
        paragraph("(МОСКОВСКИЙ ПОЛИТЕХ)", "heading"),
        Spacer(1, 13),
        paragraph("ПРИКАЗ", "order"),
        Spacer(1, 14),
        requisites(order_date, order.number),
        Spacer(1, 18.5),
        paragraph(title, "left"),
        Spacer(1, 32),
        paragraph(
            "В целях оценки качества подготовки обучающихся в соответствии с положением о внутренней системе оценки качества образовательной деятельности и подготовке обучающихся по основным образовательным программам высшего образования – программ бакалавриата, программ специалитета, программ магистратуры в Московском политехническом университете и его филиалах, утвержденным приказом от 15.10.2022 №\u00a01058-ОД"
        ),
        paragraph("ПРИКАЗЫВАЮ:", "command"),
        paragraph(
            f"1. Провести проверку остаточных знаний обучающихся в форме тестирования по дисциплинам, освоенным в {previous_semester} семестре {previous_year} учебного года, в период с {day('testingStartDate')} по {day('testingEndDate')}."
        ),
        paragraph(
            "2. Утвердить рекомендации по организации и проведению проверки остаточных знаний обучающихся Университета (Приложение № 1)."
        ),
        paragraph(
            f"3. Деканам факультетов/директорам институтов организовать и провести проверку остаточных знаний, в соответствии с рекомендациями, и представить отчеты о проверке остаточных знаний {deadline} в отдел контроля образовательного процесса в соответствии с Приложением № 2."
        ),
        paragraph(
            f"4. Начальник отдела контроля образовательного процесса {fields['bossControl']} обеспечивает методическое сопровождение сотрудников факультетов/институтов, ответственных за организацию и проведение проверки."
        ),
        paragraph(
            f"5. Контроль за исполнением настоящего приказа осуществляет начальник центра по учебно-методической работе {fields['bossMethod']}."
        ),
        Spacer(1, 32),
        borderless_table(
            [
                [
                    paragraph("Проректор по учебной работе", "left"),
                    paragraph("Г.Х. Шарипзянова", "right"),
                ]
            ],
            [WIDTH * 0.6, WIDTH * 0.4],
        ),
        PageBreak(),
        appendix_stamp(1, order_date, order.number),
        Spacer(1, 30),
        paragraph(
            "Рекомендации по организации и проведению проверки\nостаточных знаний обучающихся Университета",
            "heading",
        ),
        Spacer(1, 8),
    ]
    first_course = "2" if order.semester == "Осень" else "1"
    recommendations = [
        "1. Проверка остаточных знаний проводится в три этапа:",
        f"– 1 этап – подготовительный (подготовка тестовых материалов; формирование списков студентов и графика тестирования) с {day('preparationStartDate')} по {day('preparationEndDate')};",
        f"– 2 этап – этап проведения тестирования с {day('testingStartDate')} по {day('testingEndDate')};",
        f"– 3 этап – этап обработки и анализа результатов, формирования отчета с {day('resultsProcessingStartDate')} по {day('checkSummaryDate')}.",
        f"2. Проверка проводится в отношении учебных групп {first_course}-3 курсов очной формы обучения бакалавриата, {first_course}-4 курсов специалитета и 1 курса магистратуры.",
        "3. Учебные группы отбираются по принципу представительства одной группы от одного профиля/специализации.",
        f"4. Для каждой группы определяются две дисциплины, изученные в {previous_semester} семестре {previous_year} учебного года.",
        "5. При отборе дисциплин необходимо учитывать следующие условия:",
        "– тестирование проводится по двум дисциплинам, формирующим универсальные (для 1 курса), общепрофессиональные и профессиональные компетенции;",
        "– в перечень дисциплин для тестирования должны быть включены дисциплины, изучение которых проходило под руководством штатных преподавателей, у которых заканчивается срок трудового договора в августе;",
        "– в перечень дисциплин для тестирования должны быть включены дисциплины (не менее одной) выпускающих кафедр, ответственных за группу и профиль/специализацию.",
        "6. Расписание тестирования по группам и аудиториям, согласованное с расписанием учебных занятий, готовят и утверждают факультеты/институты.",
        "7. В тестировании должны принять участие не менее 50% студентов.",
        "8. Тестирование, обработка и анализ результатов, а также формирование отчетов проводятся ответственными лицами, назначенными деканами факультетов/директорами институтов.",
        f"9. Отчет о проверке остаточных знаний представляется в отдел контроля образовательного процесса {deadline}.",
    ]
    if all(fields.get(key) for key in ("surveyStartDate", "surveyEndDate", "surveySummaryDate")):
        recommendations.append(
            f"10. Анкетирование проводится с {day('surveyStartDate')} по {day('surveyEndDate')}; сводный отчет по анкетированию представляется до {day('surveySummaryDate')}.",
        )
    story.extend(paragraph(text) for text in recommendations)
    story.extend([PageBreak(), appendix_stamp(2, order_date, order.number), Spacer(1, 30)])
    story.extend(report_form(order.year))
    buffer = io.BytesIO()
    # A padding-free frame keeps the table, text and footer on the same left edge.
    document = BaseDocTemplate(buffer, pagesize=A4, title=order.title, author="Московский Политех")
    document.addPageTemplates(
        [
            PageTemplate(
                id=name,
                frames=[
                    Frame(
                        LEFT,
                        bottom,
                        WIDTH,
                        PAGE_HEIGHT - top - bottom,
                        leftPadding=0,
                        rightPadding=0,
                        topPadding=0,
                        bottomPadding=0,
                    )
                ],
                onPage=page_decoration,
                autoNextPageTemplate="Continuation",
            )
            for name, top in [("Order", 8), ("Continuation", 28.35)]
        ]
    )
    document.build(story)
    return buffer.getvalue()
