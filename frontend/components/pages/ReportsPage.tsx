"use client";
import { useEffect, useState } from "react";
import Page, { Notice } from "@/components/Page";
import Button from "@/components/button/Button";
import Capsule from "@/components/capsule/Capsule";
import Dropdown from "@/components/dropdown/Dropdown";
import Table, { Column } from "@/components/table/Table";
import Pagination from "@/components/pagination/Pagination";
import Modal from "@/components/modal/Modal";
import Dropzone from "@/components/dropzone/Dropzone";
import { useUser } from "@/contexts/UserContext";
import { useAction, useList, usePeriod } from "@/lib/hooks";
import {
  Department,
  Discipline,
  isManager,
  ReportRow,
  statuses,
} from "@/lib/types";
import { download, request } from "@/lib/api";
import ResultsEditor from "./ResultsEditor";

export default function ReportsPage() {
  const { userData } = useUser(),
    manager = isManager(userData),
    reviewer = manager || userData?.role === "DEPARTMENT_HEAD",
    teacher = userData?.role === "TEACHER";
  const periods = usePeriod(),
    units = useList<Department>("/departments"),
    disciplines = useList<Discipline>("/disciplines");
  const [faculty, setFaculty] = useState(""),
    [department, setDepartment] = useState(""),
    [discipline, setDiscipline] = useState(""),
    [electronic, setElectronic] = useState(""),
    [paper, setPaper] = useState("");
  const [page, setPage] = useState(1),
    [selected, setSelected] = useState<ReportRow | null>(null),
    [editing, setEditing] = useState<ReportRow | null>(null),
    [comment, setComment] = useState(""),
    [version, setVersion] = useState("electronic");
  const action = useAction();
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries({
    period_id: periods.id,
    faculty_id: manager ? faculty : "",
    department_id: department,
    discipline_id: discipline,
    electronic_status: electronic,
    paper_status: periods.selected?.paper_reports_required ? paper : "",
  }))
    if (value) query.set(key, value);
  const rows = useList<ReportRow>(
    periods.id ? `/reports/overview?${query}` : null,
  );
  const available = useList<ReportRow>(
    periods.id ? `/reports/overview?period_id=${periods.id}` : null,
  );
  useEffect(
    () => setPage(1),
    [periods.id, faculty, department, discipline, electronic, paper],
  );
  const facultyUnits = units.data.filter((unit) =>
    ["FACULTY", "INSTITUTE"].includes(unit.type),
  );
  const facultyScope = manager
    ? Number(faculty) || null
    : userData?.role === "DEPARTMENT_HEAD"
      ? userData.department_id
      : null;
  function inFaculty(unit: Department) {
    const seen = new Set<number>();
    let current: Department | undefined = unit;
    while (current && !seen.has(current.id)) {
      if (current.id === facultyScope) return true;
      seen.add(current.id);
      current = units.data.find((parent) => parent.id === current!.parent_id);
    }
    return false;
  }
  const scopedRows = available.data.filter(
    (row) => !facultyScope || row.faculty_id === facultyScope,
  );
  const chairs = units.data.filter(
    (unit) =>
      (unit.type === "DEPARTMENT" && (!facultyScope || inFaculty(unit))) ||
      scopedRows.some((row) => row.department_id === unit.id),
  );
  const options = (records: { id: number; name: string }[], label: string) => [
    { value: "", label },
    ...records.map((row) => ({ value: String(row.id), label: row.name })),
  ];
  const statusOptions = [
    { value: "", label: "Любой статус" },
    ...["MISSING", "DRAFT", "SUBMITTED", "APPROVED", "REJECTED"].map(
      (value) => ({ value, label: statuses[value] }),
    ),
  ];
  const tag = (value: string) => (
    <Capsule
      variant={
        value === "APPROVED" || value === "COMPLETE"
          ? "success"
          : value === "REJECTED"
            ? "danger"
            : "default"
      }
    >
      {statuses[value] || value}
    </Capsule>
  );
  const columns: Column<ReportRow>[] = [
    ...(manager
      ? [{ header: "Факультет / институт", accessor: "faculty_name" as const }]
      : []),
    { header: "Кафедра", accessor: (row) => row.department_name || "—" },
    { header: "Группа", accessor: "group_name" },
    { header: "Дисциплина", accessor: "discipline_name" },
    {
      header: "Электронный отчёт",
      accessor: (row) => tag(row.electronic_status),
    },
    { header: "Бумажный отчёт", accessor: (row) => tag(row.paper_status) },
    {
      header: "Участвовали ≥ 50%",
      accessor: (row) => (
        <span
          className="bool-value"
          title={`${row.participated_students} из ${row.total_students} студентов (${row.participation_percentage}%)`}
        >
          {String(row.at_least_half_participated)}
          <br />
          <small>
            {row.participated_students} / {row.total_students} ·{" "}
            {row.participation_percentage}%
          </small>
        </span>
      ),
    },
    { header: "Итог", accessor: (row) => tag(row.final_status) },
    {
      header: "",
      accessor: (row) => (
        <div className="row-actions">
          <Button
            title="Подробнее"
            color="btn-blue"
            onClick={() => {
              setSelected(row);
              setComment("");
              setVersion("electronic");
            }}
          />
          {teacher && (
            <Button
              title="Ведомость"
              color="btn-blue"
              onClick={() => setEditing(row)}
            />
          )}
        </div>
      ),
    },
  ];
  async function review(approved: boolean) {
    if (!selected?.report_id) return;
    await request(
      `/report-workflow/${selected.report_id}/review/${version}`,
      "PUT",
      { approved, comment: comment || null },
    );
    setSelected(null);
    rows.reload();
  }
  const displayedPage = Math.min(
    page,
    Math.max(1, Math.ceil(rows.data.length / 10)),
  );
  return (
    <Page
      title={
        userData?.role === "DEPARTMENT_HEAD"
          ? "Рассмотрение документов"
          : "Отчёты"
      }
    >
      <Notice text={action.notice} error={action.failed} />
      <Notice
        text={periods.error || units.error || disciplines.error || rows.error}
        error
      />
      <div className="filter-grid">
        <Dropdown
          label="Семестр"
          options={periods.data.map((row) => ({
            value: String(row.id),
            label: row.name,
          }))}
          value={periods.id}
          onChange={(value) => {
            periods.setId(value);
            setPaper("");
            setSelected(null);
          }}
        />
        {manager ? (
          <Dropdown
            label="Факультет / институт"
            options={options(facultyUnits, "Все факультеты")}
            value={faculty}
            onChange={(value) => {
              setFaculty(value);
              setDepartment("");
              setDiscipline("");
            }}
          />
        ) : (
          userData?.role === "DEPARTMENT_HEAD" && (
            <p>
              Факультет:{" "}
              <strong>
                {units.data.find((unit) => unit.id === userData.department_id)
                  ?.name || "Не назначен"}
              </strong>
            </p>
          )
        )}
        <Dropdown
          label="Кафедра"
          options={options(chairs, "Все кафедры")}
          value={department}
          onChange={(value) => {
            setDepartment(value);
            setDiscipline("");
          }}
        />
        <Dropdown
          label="Дисциплина"
          options={options(
            disciplines.data.filter(
              (row) =>
                (!department || row.department_id === Number(department)) &&
                (!facultyScope ||
                  scopedRows.some((report) => report.discipline_id === row.id)),
            ),
            "Все дисциплины",
          )}
          value={discipline}
          onChange={setDiscipline}
        />
        <Dropdown
          label="Статус электронного отчёта"
          options={statusOptions}
          value={electronic}
          onChange={setElectronic}
        />
        {periods.selected?.paper_reports_required && (
          <Dropdown
            label="Статус бумажного отчёта"
            options={statusOptions}
            value={paper}
            onChange={setPaper}
          />
        )}
      </div>
      {manager && periods.selected && (
        <div className="policy-setting">
          <label>
            <input
              type="checkbox"
              checked={periods.selected.paper_reports_required}
              disabled={action.busy}
              onChange={(event) => {
                const required = event.target.checked;
                const identifier = periods.selected!.id;
                const previous = periods.selected!.paper_reports_required;
                const setPolicy = (value: boolean) =>
                  periods.setData((current) =>
                    current.map((row) =>
                      row.id === identifier
                        ? { ...row, paper_reports_required: value }
                        : row,
                    ),
                  );
                setPolicy(required);
                action.run(async () => {
                  try {
                    await request(
                      `/periods/${identifier}/report-policy`,
                      "PATCH",
                      { paper_reports_required: required },
                    );
                  } catch (error) {
                    setPolicy(previous);
                    throw error;
                  }
                  rows.reload();
                });
              }}
            />
            Принимать бумажные отчёты в выбранном семестре
          </label>
        </div>
      )}
      <p className="field-help">
        Электронный отчёт обязателен всегда. Участие: число студентов со
        статусом «Прошёл тестирование» / полный состав группы; true при доле ≥
        50%. Для пустой группы — false.
      </p>
      {rows.loading ? (
        <p role="status">Загрузка отчётов…</p>
      ) : (
        <>
          <div className="document-statistics">
            <p>
              Электронные отчёты:{" "}
              {
                rows.data.filter((row) => row.electronic_status === "APPROVED")
                  .length
              }{" "}
              из {rows.data.length}
            </p>
            {periods.selected?.paper_reports_required && (
              <p>
                Бумажные отчёты:{" "}
                {
                  rows.data.filter((row) => row.paper_status === "APPROVED")
                    .length
                }{" "}
                из {rows.data.length}
              </p>
            )}
          </div>
          <Table
            columns={columns}
            data={rows.data.slice((displayedPage - 1) * 10, displayedPage * 10)}
          />
          {!rows.data.length && <p>Отчёты по выбранным условиям не найдены.</p>}
          <Pagination
            currentPage={displayedPage}
            totalPages={Math.max(1, Math.ceil(rows.data.length / 10))}
            onPageChange={setPage}
          />
        </>
      )}
      {manager && periods.id && (
        <div>
          <Button
            title="Скачать сводный отчёт CSV"
            color="btn-blue"
            onClick={() =>
              action.run(() =>
                download(`/exports/summary/${periods.id}.csv`, "summary.csv"),
              )
            }
          />
        </div>
      )}
      <Modal
        open={!!selected}
        onClose={() => setSelected(null)}
        title="Отчёт проверки"
      >
        {selected && (
          <>
            <p>
              {selected.group_name} — {selected.discipline_name}
            </p>
            <p>
              {selected.faculty_name} · {selected.department_name} ·{" "}
              {selected.teacher_name || "Преподаватель не назначен"}
            </p>
            <p>
              Участвовали {selected.participated_students} из{" "}
              {selected.total_students}; ≥ 50%:{" "}
              <strong>{String(selected.at_least_half_participated)}</strong>
            </p>
            <p>{selected.electronic_comment || selected.paper_comment}</p>
            <Notice text={action.notice} error={action.failed} />
            <div className="row-actions">
              {selected.has_file && (
                <Button
                  title="Скачать файл"
                  color="btn-blue"
                  onClick={() =>
                    action.run(() =>
                      download(
                        `/report-workflow/${selected.report_id}/file`,
                        "report.docx",
                      ),
                    )
                  }
                />
              )}
              <>
                <Button
                  title="Скачать бланк DOCX"
                  color="btn-blue"
                  onClick={() =>
                    action.run(() =>
                      download(
                        `/exports/report/${selected.knowledge_test_id}.docx?template=true`,
                        "report-template.docx",
                      ),
                    )
                  }
                />
                <Button
                  title="Бланк PDF"
                  color="btn-blue"
                  onClick={() =>
                    action.run(() =>
                      download(
                        `/exports/report/${selected.knowledge_test_id}.pdf?template=true`,
                        "report-template.pdf",
                      ),
                    )
                  }
                />
                <Button
                  title="Отчёт PDF"
                  color="btn-blue"
                  onClick={() =>
                    action.run(() =>
                      download(
                        `/exports/report/${selected.knowledge_test_id}.pdf`,
                        "report.pdf",
                      ),
                    )
                  }
                />
                <Button
                  title="Сформировать DOCX"
                  color="btn-blue"
                  onClick={() =>
                    action.run(() =>
                      download(
                        `/exports/report/${selected.knowledge_test_id}.docx`,
                        "report.docx",
                      ),
                    )
                  }
                />
              </>
              {teacher && (
                <>
                  <Button
                    title="Создать карточку"
                    color="btn-blue"
                    disabled={action.busy || !!selected.report_id}
                    onClick={() =>
                      action.run(async () => {
                        await request(
                          `/report-workflow/testing/${selected.knowledge_test_id}`,
                          "POST",
                        );
                        setSelected(null);
                        rows.reload();
                      })
                    }
                  />
                  {selected.report_id && (
                    <>
                      <Button
                        title="Отозвать отчёт"
                        color="btn-orange"
                        disabled={action.busy}
                        onClick={() =>
                          action.run(async () => {
                            await request(
                              `/report-workflow/${selected.report_id}/withdraw`,
                              "POST",
                            );
                            setSelected(null);
                            rows.reload();
                          })
                        }
                      />
                      <Dropzone
                        title="Файл отчёта"
                        hint="Перетащите PDF / DOCX или нажмите для выбора, до 20 МБ"
                        accept=".pdf,.docx"
                        disabled={action.busy}
                        onFile={(file) =>
                          action.run(async () => {
                            const data = new FormData();
                            data.append("file", file);
                            await request(
                              `/report-workflow/${selected.report_id}/file`,
                              "POST",
                              data,
                            );
                            setSelected(null);
                            rows.reload();
                          })
                        }
                      />
                      <label className="native-field">
                        Преподаватель предыдущего семестра
                        <input
                          maxLength={255}
                          value={selected.previous_teacher_name || ""}
                          onChange={(event) =>
                            setSelected({
                              ...selected,
                              previous_teacher_name: event.target.value,
                            })
                          }
                        />
                      </label>
                      <Button
                        title="Сохранить сведения отчёта"
                        color="btn-blue"
                        disabled={action.busy}
                        onClick={() =>
                          action.run(async () => {
                            await request(
                              `/report-workflow/${selected.report_id}/metadata`,
                              "PUT",
                              {
                                previous_teacher_name:
                                  selected.previous_teacher_name || null,
                              },
                            );
                            rows.reload();
                          })
                        }
                      />
                      {["DRAFT", "REJECTED"].includes(
                        selected.electronic_status,
                      ) && (
                        <Button
                          title="Удалить черновик отчёта"
                          color="btn-red"
                          disabled={action.busy}
                          onClick={() => {
                            if (confirm("Удалить черновик отчёта?"))
                              action.run(async () => {
                                await request(
                                  `/report-workflow/${selected.report_id}`,
                                  "DELETE",
                                );
                                setSelected(null);
                                rows.reload();
                              });
                          }}
                        />
                      )}
                    </>
                  )}
                </>
              )}
            </div>
            {reviewer && selected.report_id && (
              <div className="form-grid">
                <label>
                  Версия
                  <select
                    aria-label="Версия"
                    value={version}
                    onChange={(event) => setVersion(event.target.value)}
                  >
                    <option value="electronic">Электронная</option>
                    {selected.paper_reports_required && (
                      <option value="paper">Бумажная</option>
                    )}
                  </select>
                </label>
                <label>
                  Замечание
                  <textarea
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                  />
                </label>
                <Button
                  title="Одобрить"
                  color="btn-green"
                  disabled={action.busy}
                  onClick={() => action.run(() => review(true))}
                />
                <Button
                  title="Отклонить"
                  color="btn-red"
                  disabled={action.busy}
                  onClick={() => action.run(() => review(false))}
                />
              </div>
            )}
          </>
        )}
      </Modal>
      <Modal
        open={!!editing}
        onClose={() => setEditing(null)}
        title="Ведомость результатов"
      >
        {editing && (
          <ResultsEditor
            key={editing.knowledge_test_id}
            testId={editing.knowledge_test_id}
            onSaved={rows.reload}
          />
        )}
      </Modal>
    </Page>
  );
}
