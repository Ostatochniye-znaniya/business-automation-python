"use client";

import { useEffect, useState } from "react";
import Page, { Notice } from "@/components/Page";
import Button from "@/components/button/Button";
import Modal from "@/components/modal/Modal";
import Pagination from "@/components/pagination/Pagination";
import Table from "@/components/table/Table";
import { request } from "@/lib/api";
import { useList } from "@/lib/hooks";
import { Period, statuses } from "@/lib/types";
import styles from "./AdminChecksPage.module.css";

type AdminCheck = {
  id: number;
  group_name: string;
  discipline_name: string;
  period_name: string;
  period_status: keyof typeof periodStatuses;
  teacher_name: string | null;
  scheduled_at: string | null;
  room: string | null;
  status: string;
  agreement_status: string;
  agreement_comment: string | null;
  electronic_status: string;
  electronic_comment: string | null;
  paper_status: string;
  paper_comment: string | null;
  stage: string;
};
type ChecksPage = { items: AdminCheck[]; total: number };
type CheckResponse<T> = { path: string; data: T } | { path: string; error: string };

const pageSize = 10;
const checkStatuses = ["PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED"];
const periodStatuses = { DRAFT: "Черновик", OPEN: "Открыт", CLOSED: "Закрыт" };
const dateFormat = new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "Europe/Moscow",
});

function useCheckRequest<T>(path: string) {
  const [response, setResponse] = useState<CheckResponse<T>>();
  useEffect(() => {
    const controller = new AbortController();
    request<T>(path, "GET", undefined, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setResponse({ path, data });
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) setResponse({ path, error: error.message });
      });
    return () => controller.abort();
  }, [path]);
  return response?.path === path ? response : undefined;
}

function CheckDetails({ id, onClose }: { id: number; onClose: () => void }) {
  const response = useCheckRequest<AdminCheck>(`/administration/checks/${id}`);
  const check = response && "data" in response ? response.data : undefined;
  const error = response && "error" in response ? response.error : "";
  const agreement = check?.agreement_status;
  const agreementLabel = agreement === "REJECTED" ? "Дата отклонена" : statuses[agreement ?? ""];
  return (
    <Modal open title={`Проверка №${id}`} onClose={onClose}>
      <Notice text={error} error />
      {!response && <Notice text="Загружаем карточку…" />}
      {check && (
        <>
          <p className={styles.stage}>{check.stage}</p>
          {check.period_status === "CLOSED" && (
            <Notice text="Семестр закрыт. Изменения по проверке недоступны." />
          )}
          <dl className={styles.details}>
            <dt>Группа</dt>
            <dd>{check.group_name}</dd>
            <dt>Дисциплина</dt>
            <dd>{check.discipline_name}</dd>
            <dt>Семестр</dt>
            <dd>{check.period_name} · {periodStatuses[check.period_status]}</dd>
            <dt>Статус проверки</dt>
            <dd>{statuses[check.status] ?? check.status}</dd>
            <dt>Преподаватель</dt>
            <dd>{check.teacher_name ?? "Не назначен"}</dd>
            <dt>Дата и время (Москва)</dt>
            <dd>
              {check.scheduled_at ? dateFormat.format(new Date(check.scheduled_at)) : "Не назначены"}
            </dd>
            <dt>Аудитория</dt>
            <dd>{check.room || "Не указана"}</dd>
            <dt>Согласование даты</dt>
            <dd>
              {check.scheduled_at ? agreementLabel ?? agreement : "Дата не назначена"}
              {check.agreement_comment && <p>{check.agreement_comment}</p>}
            </dd>
            <dt>Электронный отчёт</dt>
            <dd>
              {statuses[check.electronic_status] ?? check.electronic_status}
              {check.electronic_comment && <p>{check.electronic_comment}</p>}
            </dd>
            <dt>Бумажный отчёт</dt>
            <dd>
              {statuses[check.paper_status] ?? check.paper_status}
              {check.paper_status !== "NOT_REQUIRED" && check.paper_comment && <p>{check.paper_comment}</p>}
            </dd>
          </dl>
        </>
      )}
    </Modal>
  );
}

export default function AdminChecksPage() {
  const periods = useList<Period>("/periods");
  const [filters, setFilters] = useState("");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const params = new URLSearchParams(filters);
  params.set("offset", String((page - 1) * pageSize));
  params.set("limit", String(pageSize));
  const response = useCheckRequest<ChecksPage>(`/administration/checks?${params}`);
  const result = response && "data" in response ? response.data : undefined;
  const error = response && "error" in response ? response.error : "";

  return (
    <Page title="Проверки">
      <form
        className="form-grid"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          const nextFilters = new URLSearchParams();
          for (const key of ["search", "period_id", "status"]) {
            const value = String(form.get(key) ?? "").trim();
            if (value) nextFilters.set(key, value);
          }
          setFilters(nextFilters.toString());
          setPage(1);
        }}
        onReset={() => {
          setFilters("");
          setPage(1);
        }}
      >
        <label>
          Группа или дисциплина
          <input name="search" type="search" maxLength={255} placeholder="Например, 261-001" />
        </label>
        <label>
          Семестр
          <select name="period_id" disabled={periods.loading || !!periods.error}>
            <option value="">Все семестры</option>
            {periods.data.map((period) => (
              <option key={period.id} value={period.id}>{period.name}</option>
            ))}
          </select>
        </label>
        <label>
          Статус проверки
          <select name="status">
            <option value="">Все статусы</option>
            {checkStatuses.map((status) => (
              <option key={status} value={status}>{statuses[status]}</option>
            ))}
          </select>
        </label>
        <button type="submit" className="btn btn-blue">Найти</button>
        <button type="reset" className={`btn ${styles.reset}`}>Сбросить</button>
      </form>
      <Notice text={periods.error} error />
      <Notice text={error} error />
      {!response && <Notice text="Загружаем проверки…" />}
      {result && (
        <>
          <Notice text={result.total ? `Найдено проверок: ${result.total}` : "Проверки не найдены."} />
          {result.items.length > 0 && (
            <Table
              data={result.items}
              columns={[
                { header: "Группа", accessor: "group_name" },
                { header: "Дисциплина", accessor: "discipline_name" },
                { header: "Семестр", accessor: "period_name" },
                { header: "Статус", accessor: (check) => statuses[check.status] ?? check.status },
                { header: "Текущий этап", accessor: "stage" },
                {
                  header: "Карточка",
                  accessor: (check) => (
                    <Button
                      title={`Открыть №${check.id}`}
                      color="btn-blue"
                      onClick={() => setSelectedId(check.id)}
                    />
                  ),
                },
              ]}
            />
          )}
          {result.total > pageSize && (
            <Pagination
              currentPage={page}
              totalPages={Math.ceil(result.total / pageSize)}
              onPageChange={setPage}
            />
          )}
        </>
      )}
      {selectedId !== null && (
        <CheckDetails key={selectedId} id={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </Page>
  );
}
