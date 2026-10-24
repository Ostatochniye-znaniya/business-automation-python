"use client";
import { useEffect, useState } from "react";
import Page, { Notice } from "@/components/Page";
import Table from "@/components/table/Table";
import Dropdown from "@/components/dropdown/Dropdown";
import Button from "@/components/button/Button";
import Modal from "@/components/modal/Modal";
import { useAction, useList, usePeriod } from "@/lib/hooks";
import { Group, Department, Period, statuses, isManager } from "@/lib/types";
import { useUser } from "@/contexts/UserContext";
import { download, getAll, request } from "@/lib/api";

type Change = {
  group_id: number;
  period_id: number;
  recommended: boolean;
  expected_version: number;
};
type Overview = Group & {
  recommendations: {
    period_id: number;
    recommended: boolean;
    version: number;
  }[];
  enrolled_period_ids: number[];
  testings: {
    period_id: number;
    discipline_name: string;
    status: string;
    scheduled_at: string | null;
  }[];
};
type Program = {
  id: number;
  name: string;
  code: string | null;
  faculty_id: number;
};
type History = {
  period_name: string;
  changed_by_name: string;
  changed_at: string;
  recommended: boolean;
};
const editable = (period: Period) =>
  period.status !== "CLOSED" &&
  period.end_date >= new Date().toLocaleDateString("en-CA");

export default function RecommendationsPage() {
  const periods = usePeriod(),
    units = useList<Department>("/departments"),
    programs = useList<Program>("/programs");
  const [faculty, setFaculty] = useState(""),
    [program, setProgram] = useState(""),
    [year, setYear] = useState(""),
    [semester, setSemester] = useState(""),
    [search, setSearch] = useState("");
  const groups = useList<Overview>(
    `/groups/testing-overview?${new URLSearchParams({ ...(faculty && { faculty_id: faculty }), ...(program && { study_program_id: program }), ...(year && { academic_year: year }), ...(semester && { semester }) })}`,
  );
  const [pending, setPending] = useState<Record<string, Change>>({}),
    [history, setHistory] = useState<{ name: string; rows: History[] } | null>(
      null,
    );
  const action = useAction(),
    { userData } = useUser();
  const canManage = isManager(userData);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (Object.keys(pending).length) event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [pending]);
  const visible = groups.data.filter((row) =>
    row.name.toLowerCase().includes(search.toLowerCase()),
  );
  const reference = periods.selected;
  const contextYear =
    year || reference?.academic_year || String(new Date().getFullYear());
  const contextSemester =
    semester || (year ? "" : String(reference?.semester || 1));
  const buckets = [[], [], []] as Period[][];
  periods.data
    .toSorted(
      (a, b) =>
        a.academic_year.localeCompare(b.academic_year) ||
        a.semester - b.semester,
    )
    .forEach((period) => {
      const diff =
        period.academic_year.localeCompare(contextYear) ||
        (contextSemester ? period.semester - Number(contextSemester) : 0);
      buckets[diff < 0 ? 0 : diff > 0 ? 2 : 1].push(period);
    });
  function change(group: Overview, period: Period, recommended: boolean) {
    const key = `${group.id}:${period.id}`,
      original = group.recommendations.find(
        (row) => row.period_id === period.id,
      );
    setPending((current) => {
      const next = { ...current };
      if (recommended === Boolean(original?.recommended)) delete next[key];
      else
        next[key] = {
          group_id: group.id,
          period_id: period.id,
          recommended,
          expected_version:
            current[key]?.expected_version ?? original?.version ?? 0,
        };
      return next;
    });
  }
  function bulk(recommended: boolean) {
    if (!reference || !editable(reference)) return;
    visible
      .filter((group) => group.enrolled_period_ids.includes(reference.id))
      .forEach((group) => change(group, reference, recommended));
  }
  const count = Object.keys(pending).length;
  const error = groups.error || units.error || programs.error || periods.error;
  return (
    <Page title="Списки рекомендуемых групп">
      <Notice text={error} error />
      <Notice text={action.notice} error={action.failed} />
      <div className="filter-grid">
        <Dropdown
          label="Факультет / институт"
          options={units.data
            .filter((row) => ["FACULTY", "INSTITUTE"].includes(row.type))
            .map((row) => ({ value: String(row.id), label: row.name }))}
          value={faculty}
          onChange={(value) => {
            setFaculty(value);
            setProgram("");
          }}
          placeholder="Все факультеты"
        />
        <Dropdown
          label="Направление подготовки"
          options={programs.data
            .filter((row) => !faculty || row.faculty_id === Number(faculty))
            .map((row) => ({
              value: String(row.id),
              label: `${row.code || ""} ${row.name}`,
            }))}
          value={program}
          onChange={setProgram}
          placeholder="Все направления"
        />
        <Dropdown
          label="Учебный год"
          options={[...new Set(periods.data.map((row) => row.academic_year))]
            .sort()
            .reverse()
            .map((value) => ({ value, label: value }))}
          value={year}
          onChange={(value) => {
            setYear(value);
            setSemester("");
          }}
          placeholder="Все годы"
        />
        <Dropdown
          label="Семестр"
          options={[
            ...new Set(
              periods.data
                .filter((row) => !year || row.academic_year === year)
                .map((row) => row.semester),
            ),
          ]
            .sort()
            .map((value) => ({
              value: String(value),
              label: `${value}-й семестр`,
            }))}
          value={semester}
          onChange={setSemester}
          placeholder="Все семестры"
        />
        <label className="native-field">
          Поиск группы
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <Dropdown
          label="Период массового выбора и выгрузки"
          options={periods.data.map((row) => ({
            value: String(row.id),
            label: row.name,
          }))}
          value={periods.id}
          onChange={periods.setId}
        />
      </div>
      <p className="notice">
        Относительно {contextYear} учебного года
        {contextSemester && `, ${contextSemester}-го семестра`}. Отметки
        показывают назначения тестирований, а не результаты студентов. ✓ —
        назначено / проведено, ◐ — проводится, × — нет назначения. Наведите на
        отметку для подробностей.
      </p>
      <div className="row-actions">
        <Button
          title="Сбросить фильтры"
          color="btn-blue"
          onClick={() => {
            setFaculty("");
            setProgram("");
            setYear("");
            setSemester("");
            setSearch("");
          }}
        />
        <Button
          title="Выбрать видимые"
          color="btn-blue"
          disabled={
            !canManage ||
            !reference ||
            !editable(reference) ||
            action.busy ||
            groups.loading
          }
          onClick={() => bulk(true)}
        />
        <Button
          title="Снять выбор видимых"
          color="btn-blue"
          disabled={
            !canManage ||
            !reference ||
            !editable(reference) ||
            action.busy ||
            groups.loading
          }
          onClick={() => bulk(false)}
        />
        <span role="status">
          {groups.loading
            ? "Загрузка групп…"
            : `Найдено групп: ${visible.length}`}
          . Несохранённых изменений: {count}
        </span>
      </div>
      <Table
        data={visible}
        columns={[
          {
            header: "Группа",
            accessor: (row) => (
              <>
                <strong>{row.name}</strong>
                <p>
                  {programs.data.find(
                    (program) => program.id === row.study_program_id,
                  )?.code || "—"}
                </p>
                <Button
                  title="История"
                  color="btn-blue"
                  onClick={() =>
                    action.run(async () =>
                      setHistory({
                        name: row.name,
                        rows: await getAll<History>(
                          `/recommendations/history?group_id=${row.id}`,
                        ),
                      }),
                    )
                  }
                />
              </>
            ),
            sortFn: (a, b) => a.name.localeCompare(b.name),
          },
          {
            header: "Курс",
            accessor: (row) =>
              row.admission_year &&
              Number(contextYear.slice(0, 4)) >= row.admission_year
                ? Number(contextYear.slice(0, 4)) - row.admission_year + 1
                : "—",
          },
          ...buckets.map((bucket, index) => ({
            header: [
              "Предыдущие тестирования",
              "Текущие тестирования",
              "Планируемые тестирования",
            ][index],
            accessor: (group: Overview) => (
              <div className="recommendation-periods">
                {!bucket.length && "—"}
                {bucket.map((period) => {
                  const tests = group.testings.filter(
                      (test) => test.period_id === period.id,
                    ),
                    active = tests.filter(
                      (test) => test.status !== "CANCELLED",
                    ),
                    original = group.recommendations.find(
                      (row) => row.period_id === period.id,
                    ),
                    changed = pending[`${group.id}:${period.id}`];
                  const selected =
                      changed?.recommended ?? Boolean(original?.recommended),
                    enrolled = group.enrolled_period_ids.includes(period.id),
                    canEdit =
                      canManage &&
                      editable(period) &&
                      enrolled &&
                      !action.busy &&
                      !groups.loading;
                  const mark = active.some(
                    (test) => test.status === "IN_PROGRESS",
                  )
                    ? "◐"
                    : active.length
                      ? "✓"
                      : index === 2
                        ? "—"
                        : "×";
                  return (
                    <div className="recommendation-period" key={period.id}>
                      <strong>
                        {period.semester === 1 ? "Осень" : "Весна"}{" "}
                        {period.academic_year}
                      </strong>
                      <span
                        role="img"
                        aria-label={
                          tests
                            .map(
                              (test) =>
                                `${test.discipline_name}: ${statuses[test.status]}`,
                            )
                            .join("; ") || "Нет назначенного тестирования"
                        }
                        title={
                          tests
                            .map(
                              (test) =>
                                `${test.discipline_name}: ${statuses[test.status]}${test.scheduled_at ? ` (${new Date(test.scheduled_at).toLocaleString("ru-RU")})` : " — дата не назначена"}`,
                            )
                            .join("; ") || "Нет назначенного тестирования"
                        }
                      >
                        {mark}
                      </span>
                      <label
                        title={
                          !enrolled
                            ? "Группа не участвует в этом периоде"
                            : !editable(period)
                              ? "Период закрыт для изменений"
                              : "Выбор группы для проверки"
                        }
                        data-dirty={!!changed}
                      >
                        <input
                          type="checkbox"
                          checked={selected}
                          disabled={!canEdit}
                          aria-label={`Рекомендовать группу ${group.name}: ${period.name}`}
                          onChange={(event) =>
                            change(group, period, event.target.checked)
                          }
                        />
                        {selected ? "Рекомендована" : "Рекомендовать"}
                        {changed && " *"}
                      </label>
                    </div>
                  );
                })}
              </div>
            ),
          })),
        ]}
      />
      <div className="row-actions">
        <Button
          title="Сохранить рекомендации"
          color="btn-blue"
          disabled={!canManage || !count || action.busy}
          onClick={() =>
            action.run(async () => {
              await request("/recommendations", "PUT", {
                changes: Object.values(pending),
              });
              setPending({});
              groups.reload();
            })
          }
        />
        <Button
          title="Отменить изменения"
          color="btn-blue"
          disabled={!count || action.busy}
          onClick={() => setPending({})}
        />
        <Button
          title="Скачать список CSV"
          color="btn-blue"
          disabled={!periods.id || !!count || action.busy}
          onClick={() =>
            action.run(() =>
              download(
                `/recommendations/export?period_id=${periods.id}${faculty ? `&faculty_id=${faculty}` : ""}${program ? `&study_program_id=${program}` : ""}`,
                "groups.csv",
              ),
            )
          }
        />
        <Button
          title="Обновить данные"
          color="btn-blue"
          disabled={!!count || action.busy}
          onClick={groups.reload}
        />
      </div>
      <Modal
        open={!!history}
        title={`История рекомендаций: ${history?.name || ""}`}
        onClose={() => setHistory(null)}
      >
        {history && (
          <>
            <p>
              {history.rows.length
                ? `Изменений: ${history.rows.length}`
                : "Рекомендации ещё не изменялись."}
            </p>
            <Table
              data={history.rows}
              columns={[
                { header: "Период", accessor: "period_name" },
                {
                  header: "Решение",
                  accessor: (row) =>
                    row.recommended ? "Рекомендована" : "Рекомендация снята",
                },
                { header: "Кто изменил", accessor: "changed_by_name" },
                {
                  header: "Когда",
                  accessor: (row) =>
                    new Date(row.changed_at).toLocaleString("ru-RU"),
                },
              ]}
            />
          </>
        )}
      </Modal>
    </Page>
  );
}
