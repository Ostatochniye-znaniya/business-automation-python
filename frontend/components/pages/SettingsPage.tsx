"use client";
import { useState } from "react";
import Page, { Notice } from "@/components/Page";
import Button from "@/components/button/Button";
import Table from "@/components/table/Table";
import Modal from "@/components/modal/Modal";
import { useAction, useList, usePeriod } from "@/lib/hooks";
import { Department, Group, Period } from "@/lib/types";
import { request } from "@/lib/api";
type Entity = {
  id: number;
  name?: string;
  full_name?: string;
  [key: string]: unknown;
};
type Field = {
  key: string;
  label: string;
  required?: boolean;
  options?: { id: number | string; name: string }[];
  numeric?: boolean;
};
export default function SettingsPage() {
  const periods = usePeriod(),
    units = useList<Department>("/departments"),
    programs = useList<{ id: number; name: string }>("/programs"),
    groups = useList<Group>("/groups");
  const [period, setPeriod] = useState<Partial<Period> | null>(null),
    [kind, setKind] = useState("departments"),
    [editing, setEditing] = useState<Record<string, unknown> | null>(null);
  const action = useAction();
  const config: Record<
    string,
    { name: string; read: string; write: string; fields: Field[] }
  > = {
    departments: {
      name: "Подразделения",
      read: "/departments",
      write: "/department-management",
      fields: [
        { key: "name", label: "Название", required: true },
        { key: "short_name", label: "Сокращение" },
        {
          key: "parent_id",
          label: "Родительское подразделение",
          numeric: true,
          options: units.data,
        },
        {
          key: "type",
          label: "Тип",
          required: true,
          options: [
            { id: "UNIVERSITY", name: "Университет" },
            { id: "INSTITUTE", name: "Институт" },
            { id: "FACULTY", name: "Факультет" },
            { id: "DEPARTMENT", name: "Кафедра" },
          ],
        },
      ],
    },
    programs: {
      name: "Направления подготовки",
      read: "/programs",
      write: "/catalog/programs",
      fields: [
        { key: "name", label: "Название", required: true },
        { key: "code", label: "Код направления" },
        {
          key: "faculty_id",
          label: "Факультет / институт",
          required: true,
          numeric: true,
          options: units.data.filter((row) =>
            ["FACULTY", "INSTITUTE"].includes(row.type),
          ),
        },
      ],
    },
    groups: {
      name: "Группы",
      read: "/groups",
      write: "/catalog/groups",
      fields: [
        { key: "name", label: "Номер группы", required: true },
        { key: "external_id", label: "Внешний номер" },
        { key: "admission_year", label: "Год поступления", numeric: true },
        {
          key: "department_id",
          label: "Подразделение",
          numeric: true,
          options: units.data,
        },
        {
          key: "study_program_id",
          label: "Направление подготовки",
          numeric: true,
          options: programs.data,
        },
      ],
    },
    disciplines: {
      name: "Дисциплины",
      read: "/disciplines",
      write: "/disciplines",
      fields: [
        { key: "name", label: "Название", required: true },
        {
          key: "department_id",
          label: "Кафедра",
          numeric: true,
          options: units.data.filter((row) => row.type === "DEPARTMENT"),
        },
      ],
    },
    students: {
      name: "Студенты",
      read: "/students",
      write: "/students",
      fields: [
        { key: "full_name", label: "ФИО", required: true },
        { key: "external_id", label: "Внешний номер" },
        {
          key: "group_id",
          label: "Группа",
          required: true,
          numeric: true,
          options: groups.data,
        },
      ],
    },
  };
  const current = config[kind],
    entities = useList<Entity>(current.read);
  async function refresh() {
    entities.reload();
    units.reload();
    programs.reload();
    groups.reload();
  }
  return (
    <Page title="Периоды и справочники">
      <Notice text={action.notice} error={action.failed} />
      <Notice text={periods.error || entities.error} error />
      <h2>Периоды</h2>
      <div>
        <Button
          title="Создать период"
          color="btn-blue"
          onClick={() =>
            setPeriod({
              name: "",
              academic_year: "2026/2027",
              semester: 1,
              start_date: "",
              end_date: "",
              status: "DRAFT",
              paper_reports_required: false,
            })
          }
        />
      </div>
      <Table
        data={periods.data}
        columns={[
          { header: "Период", accessor: "name" },
          { header: "Начало", accessor: "start_date" },
          { header: "Окончание", accessor: "end_date" },
          {
            header: "Доступ",
            accessor: (row) =>
              ({ DRAFT: "Черновик", OPEN: "Открыт", CLOSED: "Закрыт" })[
                row.status
              ] || row.status,
          },
          {
            header: "Бумажные отчёты",
            accessor: (row) =>
              row.paper_reports_required ? "Включены" : "Отключены",
          },
          {
            header: "",
            accessor: (row) => (
              <Button
                title="Изменить"
                color="btn-blue"
                onClick={() => setPeriod({ ...row })}
              />
            ),
          },
        ]}
      />
      <h2>Учебные справочники</h2>
      <div className="form-grid">
        <label>
          Справочник
          <select
            value={kind}
            onChange={(event) => setKind(event.target.value)}
          >
            {Object.entries(config).map(([key, value]) => (
              <option key={key} value={key}>
                {value.name}
              </option>
            ))}
          </select>
        </label>
        <Button
          title="Добавить запись"
          color="btn-blue"
          onClick={() => setEditing({})}
        />
      </div>
      <Table
        data={entities.data}
        columns={[
          {
            header: "Название / ФИО",
            accessor: (row) => row.name || row.full_name || "—",
          },
          {
            header: "",
            accessor: (row) => (
              <Button
                title="Изменить"
                color="btn-blue"
                onClick={() => setEditing({ ...row })}
              />
            ),
          },
        ]}
      />
      <Modal
        open={!!period}
        title="Период проверки"
        onClose={() => setPeriod(null)}
      >
        {period && (
          <form
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              action.run(async () => {
                const { id, ...data } = period;
                await request(
                  "/periods" + (id ? "/" + id : ""),
                  id ? "PUT" : "POST",
                  data,
                );
                setPeriod(null);
                periods.reload();
              });
            }}
          >
            <Notice text={action.notice} error={action.failed} />
            {(["name", "academic_year", "start_date", "end_date"] as const).map(
              (key, index) => (
                <label key={key}>
                  {["Название", "Учебный год", "Начало", "Окончание"][index]}
                  <input
                    required
                    type={key.endsWith("date") ? "date" : "text"}
                    value={period[key] || ""}
                    onChange={(event) =>
                      setPeriod({ ...period, [key]: event.target.value })
                    }
                  />
                </label>
              ),
            )}
            <label>
              Семестр
              <select
                value={period.semester}
                onChange={(event) =>
                  setPeriod({ ...period, semester: Number(event.target.value) })
                }
              >
                <option value={1}>Осень</option>
                <option value={2}>Весна</option>
              </select>
            </label>
            <label>
              Доступ
              <select
                value={period.status}
                onChange={(event) =>
                  setPeriod({ ...period, status: event.target.value })
                }
              >
                <option value="DRAFT">Черновик</option>
                <option value="OPEN">Открыт</option>
                <option value="CLOSED">Закрыт</option>
              </select>
            </label>
            <label>
              Бумажные отчёты
              <select
                value={String(period.paper_reports_required)}
                onChange={(event) =>
                  setPeriod({
                    ...period,
                    paper_reports_required: event.target.value === "true",
                  })
                }
              >
                <option value="false">Отключены</option>
                <option value="true">Включены</option>
              </select>
            </label>
            <button className="btn btn-blue" disabled={action.busy}>
              Сохранить период
            </button>
          </form>
        )}
      </Modal>
      <Modal
        open={!!editing}
        title={current.name}
        onClose={() => setEditing(null)}
      >
        {editing && (
          <form
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              action.run(async () => {
                const payload: Record<string, unknown> = {};
                for (const field of current.fields)
                  payload[field.key] = editing[field.key] ?? null;
                if (kind === "groups")
                  payload.period_ids = periods.id ? [Number(periods.id)] : [];
                await request(
                  current.write + (editing.id ? "/" + editing.id : ""),
                  editing.id ? "PUT" : "POST",
                  payload,
                );
                setEditing(null);
                await refresh();
              });
            }}
          >
            <Notice text={action.notice} error={action.failed} />
            {current.fields.map((field) => (
              <label key={field.key}>
                {field.label}
                {field.options ? (
                  <select
                    required={field.required}
                    value={String(editing[field.key] ?? "")}
                    onChange={(event) =>
                      setEditing({
                        ...editing,
                        [field.key]: event.target.value
                          ? field.numeric
                            ? Number(event.target.value)
                            : event.target.value
                          : null,
                      })
                    }
                  >
                    <option value="">Не выбрано</option>
                    {field.options.map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    required={field.required}
                    type={field.numeric ? "number" : "text"}
                    value={String(editing[field.key] ?? "")}
                    onChange={(event) =>
                      setEditing({
                        ...editing,
                        [field.key]: event.target.value
                          ? field.numeric
                            ? Number(event.target.value)
                            : event.target.value
                          : null,
                      })
                    }
                  />
                )}
              </label>
            ))}
            <button className="btn btn-blue" disabled={action.busy}>
              Сохранить запись
            </button>
            {kind === "departments" && !!editing.id && (
              <Button
                title="Удалить подразделение"
                color="btn-red"
                disabled={action.busy}
                onClick={() => {
                  if (confirm("Удалить подразделение?"))
                    action.run(async () => {
                      await request(
                        `/department-management/${editing.id}`,
                        "DELETE",
                      );
                      setEditing(null);
                      await refresh();
                    });
                }}
              />
            )}
          </form>
        )}
      </Modal>
    </Page>
  );
}
