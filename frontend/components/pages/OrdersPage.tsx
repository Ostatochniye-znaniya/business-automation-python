"use client";
import { useState } from "react";
import Page, { Notice } from "@/components/Page";
import Table from "@/components/table/Table";
import Button from "@/components/button/Button";
import Modal from "@/components/modal/Modal";
import { request } from "@/lib/api";
import { useAction, useList } from "@/lib/hooks";
type Order = {
  id?: number;
  title: string;
  year: string;
  semester: string;
  date: string;
  draft: boolean;
  details: Record<string, string>;
};
const blank = (): Order => ({
  title: "",
  year: String(new Date().getFullYear()),
  semester: "Осень",
  date: new Date().toLocaleDateString("en-CA"),
  draft: true,
  details: {},
});
export default function OrdersPage() {
  const orders = useList<Order>("/orders"),
    [editing, setEditing] = useState<Order | null>(null),
    [search, setSearch] = useState("");
  const action = useAction();
  async function save(draft: boolean) {
    if (!editing) return;
    await request(
      `/orders${editing.id ? "/" + editing.id : ""}`,
      editing.id ? "PUT" : "POST",
      { ...editing, draft },
    );
    setEditing(null);
    orders.reload();
  }
  return (
    <Page title="Приказы">
      <Notice
        text={orders.error || action.notice}
        error={!!orders.error || action.failed}
      />
      <div className="form-grid">
        <label>
          Поиск
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <Button
          title="Сформировать новый приказ"
          color="btn-blue"
          onClick={() => setEditing(blank())}
        />
      </div>
      <Table
        data={orders.data.filter((row) =>
          row.title.toLowerCase().includes(search.toLowerCase()),
        )}
        columns={[
          { header: "№", accessor: (row) => row.id },
          { header: "Название", accessor: "title" },
          { header: "Учебный год", accessor: "year" },
          { header: "Семестр", accessor: "semester" },
          {
            header: "Статус",
            accessor: (row) => (row.draft ? "Черновик" : "Опубликован"),
          },
          {
            header: "",
            accessor: (row) => (
              <Button
                title="Подробнее"
                color="btn-blue"
                onClick={() =>
                  setEditing({ ...row, details: { ...row.details } })
                }
              />
            ),
          },
        ]}
      />
      <Modal open={!!editing} title="Приказ" onClose={() => setEditing(null)}>
        {editing && (
          <form
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              action.run(() => save(true));
            }}
          >
            <Notice text={action.notice} error={action.failed} />
            {(["title", "year", "semester", "date"] as const).map(
              (key, index) => (
                <label key={key}>
                  {["Название", "Учебный год", "Семестр", "Дата"][index]}
                  {key === "semester" ? (
                    <select
                      disabled={editing.id !== undefined && !editing.draft}
                      value={editing[key]}
                      onChange={(event) =>
                        setEditing({ ...editing, [key]: event.target.value })
                      }
                    >
                      <option>Весна</option>
                      <option>Осень</option>
                    </select>
                  ) : (
                    <input
                      required
                      disabled={editing.id !== undefined && !editing.draft}
                      type={key === "date" ? "date" : "text"}
                      value={editing[key]}
                      onChange={(event) =>
                        setEditing({ ...editing, [key]: event.target.value })
                      }
                    />
                  )}
                </label>
              ),
            )}
            {[
              ["bossControl", "Начальник отдела контроля"],
              ["bossMethod", "Начальник учебно-методического центра"],
              ["checkSummaryDate", "Сводный отчёт до"],
              ["reportsDate", "Отчёты по результатам до"],
              ["surveyDate", "Дата анкетирования"],
            ].map(([key, label]) => (
              <label key={key}>
                {label}
                <input
                  type={key.includes("Date") ? "date" : "text"}
                  disabled={editing.id !== undefined && !editing.draft}
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
            {(!editing.id || editing.draft) && (
              <div className="row-actions">
                <button className="btn btn-blue" disabled={action.busy}>
                  Сохранить черновик
                </button>
                <Button
                  title="Опубликовать"
                  color="btn-green"
                  disabled={action.busy || !editing.title}
                  onClick={() => {
                    if (
                      confirm(
                        "После публикации редактирование недоступно. Опубликовать?",
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
              </div>
            )}
          </form>
        )}
      </Modal>
    </Page>
  );
}
