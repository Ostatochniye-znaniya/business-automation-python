"use client";
import { useRef, useState } from "react";
import Page, { Notice } from "@/components/Page";
import Table from "@/components/table/Table";
import Button from "@/components/button/Button";
import Modal from "@/components/modal/Modal";
import { download, request } from "@/lib/api";
import { useAction, useList, usePeriod } from "@/lib/hooks";

type Order = {
  id?: number;
  title: string;
  number: string | null;
  year: string;
  semester: string;
  date: string;
  draft: boolean;
  period_id: number | null;
  details: Record<string, string>;
};
const blank = (): Order => ({
  title: "О проведении проверки остаточных знаний обучающихся",
  number: "",
  year: "",
  semester: "Осень",
  date: new Date().toLocaleDateString("en-CA"),
  draft: true,
  period_id: null,
  details: {},
});
const detailFields = [
  [
    "bossControl",
    "Начальник отдела контроля образовательного процесса",
    "text",
  ],
  ["bossMethod", "Начальник центра по учебно-методической работе", "text"],
  ["preparationStartDate", "Начало подготовительного этапа", "date"],
  ["preparationEndDate", "Окончание подготовительного этапа", "date"],
  ["testingStartDate", "Начало тестирования", "date"],
  ["testingEndDate", "Окончание тестирования", "date"],
  ["resultsProcessingStartDate", "Начало обработки результатов", "date"],
  ["checkSummaryDate", "Сводный отчёт по результатам проверки до", "date"],
  ["surveyStartDate", "Начало анкетирования", "date"],
  ["surveyEndDate", "Окончание анкетирования", "date"],
  ["surveySummaryDate", "Сводный отчёт по анкетированию до", "date"],
  ["electronicReportDeadline", "Сдача электронных отчётов до", "date"],
  ["paperReportDeadline", "Сдача бумажных отчётов до", "date"],
];
export default function OrdersPage() {
  const orders = useList<Order>("/orders"),
    periods = usePeriod(),
    action = useAction();
  const [editing, setEditing] = useState<Order | null>(null),
    [search, setSearch] = useState(""),
    [drafts, setDrafts] = useState(false),
    [cards, setCards] = useState(false);
  const form = useRef<HTMLFormElement>(null);
  const locked = !!editing?.id && !editing.draft;
  const selectedPeriod = periods.data.find(
    (row) => row.id === editing?.period_id,
  );
  const paper = locked
    ? editing?.details.paperReportsRequired === "true"
    : selectedPeriod?.paper_reports_required;
  const rows = orders.data.filter(
    (row) =>
      row.draft === drafts &&
      `${row.title} ${row.number || ""} ${row.year}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  function create() {
    const period = periods.selected;
    setEditing({
      ...blank(),
      period_id: period?.id || null,
      year: period?.academic_year || "",
      semester: period?.semester === 2 ? "Весна" : "Осень",
    });
  }
  async function save(draft: boolean) {
    if (!editing) return;
    await request(
      `/orders${editing.id ? `/${editing.id}` : ""}`,
      editing.id ? "PUT" : "POST",
      { ...editing, draft },
    );
    setEditing(null);
    setDrafts(draft);
    orders.reload();
  }
  return (
    <Page title={drafts ? "Черновики приказов" : "Приказы"}>
      <Notice
        text={orders.error || periods.error || action.notice}
        error={!!orders.error || !!periods.error || action.failed}
      />
      <div className="row-actions">
        <Button
          title="Сформировать новый приказ"
          color="btn-blue"
          onClick={create}
        />
        <Button
          title={drafts ? "Приказы" : "Черновики"}
          color="btn-purple"
          onClick={() => setDrafts(!drafts)}
        />
        <Button
          title={cards ? "Таблица" : "Карточки"}
          color="btn-blue"
          onClick={() => setCards(!cards)}
        />
      </div>
      <label className="native-field">
        Поиск по номеру, названию, учебному году
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </label>
      {!rows.length && (
        <p className="notice">
          {orders.loading ? "Загрузка…" : "Приказы не найдены."}
        </p>
      )}
      {cards ? (
        <div className="order-cards">
          {rows.map((row) => (
            <article className="notice" key={row.id}>
              <h2>
                № {row.number || "—"} — {row.title}
              </h2>
              <p>
                {row.year}, {row.semester},{" "}
                {new Date(row.date).toLocaleDateString("ru-RU")}
              </p>
              <Button
                title="Подробнее"
                color="btn-blue"
                onClick={() =>
                  setEditing({ ...row, details: { ...row.details } })
                }
              />
            </article>
          ))}
        </div>
      ) : (
        <Table
          data={rows}
          columns={[
            { header: "№", accessor: (row) => row.number || "—" },
            { header: "Название", accessor: "title" },
            { header: "Учебный год", accessor: "year" },
            { header: "Семестр", accessor: "semester" },
            {
              header: "Дата",
              accessor: (row) => new Date(row.date).toLocaleDateString("ru-RU"),
            },
            {
              header: "",
              accessor: (row) => (
                <div className="row-actions">
                  <Button
                    title="Подробнее"
                    color="btn-blue"
                    onClick={() =>
                      setEditing({ ...row, details: { ...row.details } })
                    }
                  />
                  {!row.draft && (
                    <Button
                      title="Скачать PDF"
                      color="btn-green"
                      onClick={() =>
                        action.run(() =>
                          download(
                            `/orders/${row.id}/file`,
                            `order-${row.number}.pdf`,
                          ),
                        )
                      }
                    />
                  )}
                </div>
              ),
            },
          ]}
        />
      )}
      <Modal
        open={!!editing}
        title={locked ? "Приказ" : "Формирование приказа"}
        onClose={() => {
          if (
            locked ||
            confirm("Закрыть форму? Несохранённые изменения будут потеряны.")
          )
            setEditing(null);
        }}
      >
        {editing && (
          <form
            ref={form}
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              action.run(() => save(false));
            }}
          >
            <Notice text={action.notice} error={action.failed} />
            <label>
              Дата приказа
              <input
                type="date"
                required
                disabled={locked}
                value={editing.date}
                onChange={(event) =>
                  setEditing({ ...editing, date: event.target.value })
                }
              />
            </label>
            <label>
              Номер приказа
              <input
                required
                maxLength={50}
                disabled={locked}
                value={editing.number || ""}
                onChange={(event) =>
                  setEditing({ ...editing, number: event.target.value })
                }
              />
            </label>
            <label>
              Название
              <input
                required
                maxLength={500}
                disabled={locked}
                value={editing.title}
                onChange={(event) =>
                  setEditing({ ...editing, title: event.target.value })
                }
              />
            </label>
            <label>
              Проверяемый семестр
              <select
                required
                disabled={locked}
                value={editing.period_id || ""}
                onChange={(event) => {
                  const period = periods.data.find(
                    (row) => row.id === Number(event.target.value),
                  );
                  setEditing({
                    ...editing,
                    period_id: period?.id || null,
                    year: period?.academic_year || "",
                    semester: period?.semester === 2 ? "Весна" : "Осень",
                  });
                }}
              >
                <option value="">Выберите период</option>
                {periods.data.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Учебный год
              <input readOnly value={editing.year} />
            </label>
            <label>
              Семестр
              <input readOnly value={editing.semester} />
            </label>
            <p className="notice">
              Электронные отчёты обязательны. Бумажные отчёты:{" "}
              {paper ? "принимаются" : "не принимаются"}. Настройка задаётся ЛПР
              в разделе отчётов для выбранного семестра.
            </p>
            {detailFields
              .filter(([key]) => key !== "paperReportDeadline" || paper)
              .map(([key, label, type]) => (
                <label key={key}>
                  {label}
                  <input
                    required
                    type={type}
                    maxLength={type === "text" ? 200 : undefined}
                    disabled={locked}
                    value={editing.details[key] || ""}
                    onChange={(event) =>
                      setEditing({
                        ...editing,
                        details: {
                          ...editing.details,
                          [key]: event.target.value,
                        },
                      })
                    }
                  />
                </label>
              ))}
            <div className="row-actions">
              {locked ? (
                <Button
                  title="Скачать PDF с приложениями"
                  color="btn-green"
                  onClick={() =>
                    action.run(() =>
                      download(
                        `/orders/${editing.id}/file`,
                        `order-${editing.number}.pdf`,
                      ),
                    )
                  }
                />
              ) : (
                <>
                  <Button
                    title="Сохранить черновик"
                    color="btn-blue"
                    disabled={action.busy || !editing.title}
                    onClick={() => action.run(() => save(true))}
                  />
                  <Button
                    title="Сформировать приказ"
                    color="btn-green"
                    disabled={action.busy}
                    onClick={() => {
                      if (
                        form.current?.reportValidity() &&
                        confirm(
                          "Сформировать приказ? После публикации его нельзя редактировать.",
                        )
                      )
                        action.run(() => save(false));
                    }}
                  />
                  {editing.id && (
                    <Button
                      title="Удалить черновик"
                      color="btn-red"
                      disabled={action.busy}
                      onClick={() => {
                        if (confirm("Удалить черновик?"))
                          action.run(async () => {
                            await request(`/orders/${editing.id}`, "DELETE");
                            setEditing(null);
                            orders.reload();
                          });
                      }}
                    />
                  )}
                </>
              )}
            </div>
          </form>
        )}
      </Modal>
    </Page>
  );
}
