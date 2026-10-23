"use client";
import { useState } from "react";
import Page, { Notice } from "@/components/Page";
import Button from "@/components/button/Button";
import Table from "@/components/table/Table";
import Modal from "@/components/modal/Modal";
import { useList, useAction } from "@/lib/hooks";
import { Department, roles, User } from "@/lib/types";
import { request } from "@/lib/api";
type AccessRequest = {
  id: number;
  user_id: number;
  requested_role: string;
  reason: string;
  status: string;
};
type Audit = {
  id: number;
  actor_id: number;
  created_at: string;
  action: string;
  entity_id: number | null;
};
const blank = () =>
  ({
    full_name: "",
    email: null,
    external_id: null,
    position: null,
    role: "GUEST",
    department_id: null,
    is_active: true,
  }) as Omit<User, "id">;
export default function AccessPage() {
  const users = useList<User>("/administration/users"),
    units = useList<Department>("/departments"),
    requests = useList<AccessRequest>("/administration/access-requests"),
    audit = useList<Audit>("/administration/audit");
  const [editing, setEditing] = useState<
      (Omit<User, "id"> & { id?: number }) | null
    >(null),
    [search, setSearch] = useState(""),
    [role, setRole] = useState(""),
    [importStatus, setImportStatus] = useState("");
  const action = useAction();
  return (
    <Page title="Права доступа">
      <Notice
        text={users.error || requests.error || audit.error || action.notice}
        error={
          !!users.error || !!requests.error || !!audit.error || action.failed
        }
      />
      <div className="form-grid">
        <label>
          Поиск сотрудника
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label>
          Роль
          <select
            value={role}
            onChange={(event) => setRole(event.target.value)}
          >
            <option value="">Все роли</option>
            {Object.entries(roles).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <Button
          title="Добавить сотрудника"
          color="btn-blue"
          onClick={() => setEditing(blank())}
        />
      </div>
      <Table
        data={users.data.filter(
          (row) =>
            (!role || row.role === role) &&
            `${row.full_name} ${row.email || ""}`
              .toLowerCase()
              .includes(search.toLowerCase()),
        )}
        columns={[
          { header: "Сотрудник", accessor: "full_name" },
          { header: "Роль", accessor: (row) => roles[row.role] },
          {
            header: "Подразделение",
            accessor: (row) =>
              units.data.find((unit) => unit.id === row.department_id)?.name ||
              "—",
          },
          {
            header: "Доступ",
            accessor: (row) => (row.is_active ? "Активен" : "Отключён"),
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
      <h2>Импорт сотрудников</h2>
      <label className="native-field">
        CSV / XLSX
        <input
          type="file"
          accept=".csv,.xlsx"
          disabled={action.busy}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file)
              action.run(async () => {
                const form = new FormData();
                form.append("file", file);
                const result = await request<{ records_processed: number }>(
                  "/administration/imports/employees",
                  "POST",
                  form,
                );
                setImportStatus(
                  `Обработано сотрудников: ${result.records_processed}`,
                );
                users.reload();
                audit.reload();
              });
          }}
        />
      </label>
      <p className="field-help">
        Заголовки: external_id, full_name, email, position, department_id. Новые
        сотрудники получают роль «Гость».
      </p>
      <Notice text={importStatus} />
      <h2>Заявки на доступ</h2>
      <Table
        data={requests.data}
        columns={[
          {
            header: "Сотрудник",
            accessor: (row) =>
              users.data.find((user) => user.id === row.user_id)?.full_name ||
              "—",
          },
          { header: "Роль", accessor: (row) => roles[row.requested_role] },
          { header: "Причина", accessor: "reason" },
          {
            header: "Статус",
            accessor: (row) =>
              ({
                PENDING: "Ожидает",
                APPROVED: "Одобрена",
                REJECTED: "Отклонена",
              })[row.status] || row.status,
          },
          {
            header: "",
            accessor: (row) =>
              row.status === "PENDING" ? (
                <div className="row-actions">
                  {[true, false].map((approved) => (
                    <Button
                      key={String(approved)}
                      title={approved ? "Одобрить" : "Отклонить"}
                      color={approved ? "btn-green" : "btn-red"}
                      disabled={action.busy}
                      onClick={() =>
                        action.run(async () => {
                          await request(
                            `/administration/access-requests/${row.id}`,
                            "PUT",
                            { approved },
                          );
                          requests.reload();
                          users.reload();
                          audit.reload();
                        })
                      }
                    />
                  ))}
                </div>
              ) : null,
          },
        ]}
      />
      <h2>Журнал действий</h2>
      <Table
        data={audit.data.slice(0, 100)}
        columns={[
          {
            header: "Время (Москва)",
            accessor: (row) =>
              new Date(row.created_at + "Z").toLocaleString("ru-RU", {
                timeZone: "Europe/Moscow",
              }),
          },
          {
            header: "Сотрудник",
            accessor: (row) =>
              users.data.find((user) => user.id === row.actor_id)?.full_name ||
              "—",
          },
          { header: "Действие", accessor: "action" },
          { header: "Объект", accessor: (row) => row.entity_id ?? "—" },
        ]}
      />
      <Modal
        open={!!editing}
        title="Карточка сотрудника"
        onClose={() => setEditing(null)}
      >
        {editing && (
          <form
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault();
              action.run(async () => {
                const { id, ...data } = editing;
                await request(
                  `/administration/users${id ? "/" + id : ""}`,
                  id ? "PUT" : "POST",
                  data,
                );
                setEditing(null);
                users.reload();
                audit.reload();
              });
            }}
          >
            <Notice text={action.notice} error={action.failed} />
            {(["full_name", "external_id", "email", "position"] as const).map(
              (key, index) => (
                <label key={key}>
                  {["ФИО", "Табельный номер", "Email", "Должность"][index]}
                  <input
                    required={key === "full_name"}
                    type={key === "email" ? "email" : "text"}
                    value={editing[key] || ""}
                    onChange={(event) =>
                      setEditing({
                        ...editing,
                        [key]: event.target.value || null,
                      })
                    }
                  />
                </label>
              ),
            )}
            <label>
              Подразделение
              <select
                value={editing.department_id || ""}
                onChange={(event) =>
                  setEditing({
                    ...editing,
                    department_id: Number(event.target.value) || null,
                  })
                }
              >
                <option value="">Не назначено</option>
                {units.data.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Роль
              <select
                value={editing.role}
                onChange={(event) =>
                  setEditing({ ...editing, role: event.target.value })
                }
              >
                {Object.entries(roles).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Доступ
              <select
                value={String(editing.is_active)}
                onChange={(event) =>
                  setEditing({
                    ...editing,
                    is_active: event.target.value === "true",
                  })
                }
              >
                <option value="true">Активен</option>
                <option value="false">Отключён</option>
              </select>
            </label>
            <button className="btn btn-blue" disabled={action.busy}>
              Сохранить сотрудника
            </button>
          </form>
        )}
      </Modal>
    </Page>
  );
}
