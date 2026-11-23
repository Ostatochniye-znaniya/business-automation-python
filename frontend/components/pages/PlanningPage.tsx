"use client";
import { useState } from "react";
import Page, { Notice } from "@/components/Page";
import Button from "@/components/button/Button";
import Dropdown from "@/components/dropdown/Dropdown";
import Table from "@/components/table/Table";
import { useList, usePeriod, useAction } from "@/lib/hooks";
import { Discipline, Group, KnowledgeTest, statuses, User } from "@/lib/types";
import { request, download } from "@/lib/api";
export default function PlanningPage({
  mode,
}: {
  mode: "groups" | "disciplines" | "teachers" | "dates" | "schedule";
}) {
  const periods = usePeriod(),
    tests = useList<KnowledgeTest>(
      periods.id ? `/workflow/testing?period_id=${periods.id}` : null,
    ),
    groups = useList<Group>("/groups"),
    disciplines = useList<Discipline>("/disciplines"),
    users = useList<User>("/users");
  const eligible = useList<Group>(
    periods.id && ["groups", "disciplines"].includes(mode)
      ? `/workflow/eligible-groups?period_id=${periods.id}`
      : null,
  );
  const [group, setGroup] = useState(""),
    [first, setFirst] = useState(""),
    [second, setSecond] = useState(""),
    [participates, setParticipates] = useState(true),
    [reason, setReason] = useState("");
  const [testId, setTestId] = useState(""),
    [teachers, setTeachers] = useState<number[]>([]),
    [date, setDate] = useState(""),
    [endDate, setEndDate] = useState(""),
    [room, setRoom] = useState(""),
    [approved, setApproved] = useState(true),
    [comment, setComment] = useState(""),
    [signatory, setSignatory] = useState("");
  const action = useAction(),
    name = (
      list: { id: number; name?: string; full_name?: string }[],
      id: number | null,
    ) =>
      list.find((row) => row.id === id)?.name ||
      list.find((row) => row.id === id)?.full_name ||
      "—";
  const active = tests.data.filter((row) => row.status !== "CANCELLED");
  const selected = tests.data.find((row) => row.id === Number(testId));
  const eligibleTeachers = useList<User>(
    testId && mode === "teachers" ? `/workflow/testing/${testId}/eligible-teachers` : null,
  );
  const titles = {
    groups: "Выбор групп",
    disciplines: "Выбор дисциплин",
    teachers: "Выбор преподавателей",
    dates: "Согласование дат",
    schedule: "Составление графика",
  };
  async function saveSelection() {
    await request("/workflow/participation", "PUT", {
      group_id: Number(group),
      period_id: Number(periods.id),
      participates,
      discipline_ids: participates ? [Number(first), Number(second)] : [],
      reason: reason || null,
    });
    tests.reload();
  }
  return (
    <Page title={titles[mode]}>
      <Notice text={action.notice} error={action.failed} />
      <Notice
        text={
          tests.error ||
          eligible.error ||
          groups.error ||
          users.error ||
          disciplines.error ||
          periods.error
        }
        error
      />
      <div className="filter-grid">
        <Dropdown
          label="Семестр"
          value={periods.id}
          onChange={(value) => {
            periods.setId(value);
            setTestId("");
            setGroup("");
          }}
          options={periods.data.map((row) => ({
            value: String(row.id),
            label: row.name,
          }))}
        />
      </div>
      {["groups", "disciplines"].includes(mode) && (
        <form
          className="form-grid"
          onSubmit={(event) => {
            event.preventDefault();
            action.run(saveSelection);
          }}
        >
          <label>
            Рекомендованная группа
            <select
              aria-label="Рекомендованная группа"
              required
              value={group}
              onChange={(event) => {
                setGroup(event.target.value);
                const existing = active.filter(
                  (row) => row.group_id === Number(event.target.value),
                );
                setFirst(String(existing[0]?.discipline_id || ""));
                setSecond(String(existing[1]?.discipline_id || ""));
              }}
            >
              <option value="">Выберите…</option>
              {eligible.data.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Участие
            <select
              value={String(participates)}
              onChange={(event) =>
                setParticipates(event.target.value === "true")
              }
            >
              <option value="true">Участвует</option>
              <option value="false">Не участвует</option>
            </select>
          </label>
          {participates && (
            <>
              <label>
                Первая дисциплина
                <select
                  aria-label="Первая дисциплина"
                  required
                  value={first}
                  onChange={(event) => setFirst(event.target.value)}
                >
                  <option value="">Выберите…</option>
                  {disciplines.data.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Вторая дисциплина
                <select
                  aria-label="Вторая дисциплина"
                  required
                  value={second}
                  onChange={(event) => setSecond(event.target.value)}
                >
                  <option value="">Выберите…</option>
                  {disciplines.data.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.name}
                    </option>
                  ))}
                </select>
              </label>
            </>
          )}
          <label>
            Комментарий
            <input
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </label>
          <button className="btn btn-blue" disabled={action.busy}>
            Сохранить выбор
          </button>
        </form>
      )}
      <Table
        data={active}
        columns={[
          {
            header: "Группа",
            accessor: (row) => name(groups.data, row.group_id),
          },
          {
            header: "Дисциплина",
            accessor: (row) => name(disciplines.data, row.discipline_id),
          },
          {
            header: "Преподаватель",
            accessor: (row) => row.assignments?.length
              ? row.assignments.map((item) => name(users.data, item.teacher_id)).join(", ")
              : name(users.data, row.teacher_id),
          },
          {
            header: "Дата / время (Москва)",
            accessor: (row) =>
              row.scheduled_at
                ? new Date(row.scheduled_at + "Z").toLocaleString("ru-RU", {
                    timeZone: "Europe/Moscow",
                  })
                : "Не назначено",
          },
          { header: "Аудитория", accessor: (row) => row.room || "—" },
          {
            header: "Согласование",
            accessor: (row) => statuses[row.agreement_status],
          },
          {
            header: "Комментарий",
            accessor: (row) => row.agreement_comment || "—",
          },
        ]}
      />
      {["teachers", "dates", "schedule"].includes(mode) && (
        <form
          className="form-grid"
          onSubmit={(event) => {
            event.preventDefault();
            action.run(async () => {
              if (mode === "dates")
                await request(`/workflow/testing/${testId}/agreement`, "PUT", {
                  approved,
                  comment: comment || null,
                  scheduled_at: approved && date ? new Date(date + "+03:00").toISOString() : null,
                });
              else
                await request(`/workflow/testing/${testId}/assignments`, "PUT", {
                  teacher_ids: teachers,
                  start_date: date,
                  end_date: endDate,
                  room,
                });
              tests.reload();
            });
          }}
        >
          <label>
            Проверка
            <select
              aria-label="Проверка"
              required
              value={testId}
              onChange={(event) => {
                setTestId(event.target.value);
                const current = active.find((row) => row.id === Number(event.target.value));
                setTeachers(current?.assignments?.map((item) => item.teacher_id) || []);
                setDate(mode === "teachers" ? current?.assignments?.[0]?.start_date || "" : "");
                setEndDate(current?.assignments?.[0]?.end_date || "");
                setRoom(current?.room || "");
              }}
            >
              <option value="">Выберите…</option>
              {active.map((row) => (
                <option key={row.id} value={row.id}>
                  {name(groups.data, row.group_id)} —{" "}
                  {name(disciplines.data, row.discipline_id)}
                </option>
              ))}
            </select>
          </label>
          {mode === "dates" ? (
            <>
              <label>
                Решение
                <select
                  value={String(approved)}
                  onChange={(event) =>
                    setApproved(event.target.value === "true")
                  }
                >
                  <option value="true">Согласовать</option>
                  <option value="false">Отклонить</option>
                </select>
              </label>
              <label>
                Причина отклонения
                <input
                  required={!approved}
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                />
              </label>
              {approved && <label>Дата и время (Москва)<input required type="datetime-local" value={date} onChange={(event) => setDate(event.target.value)} /></label>}
            </>
          ) : (
            <>
              <label>
                Преподаватели
                <select
                  aria-label="Преподаватели"
                  required
                  multiple
                  size={5}
                  value={teachers.map(String)}
                  onChange={(event) => setTeachers(Array.from(event.target.selectedOptions, (option) => Number(option.value)))}
                >
                  {eligibleTeachers.data
                    .map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.full_name}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Начало интервала
                <input
                  required
                  type="date"
                  value={date}
                  onChange={(event) => setDate(event.target.value)}
                />
              </label>
              <label>Конец интервала<input required type="date" min={date} value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label>
              <label>
                Аудитория
                <input
                  required
                  value={room}
                  onChange={(event) => setRoom(event.target.value)}
                />
              </label>
            </>
          )}
          <button className="btn btn-blue" disabled={action.busy}>
            Сохранить
          </button>
        </form>
      )}
      <div className="form-grid">
        <label>
          Подписант графика
          <input
            value={signatory}
            onChange={(event) => setSignatory(event.target.value)}
            placeholder="Декан / директор института"
          />
        </label>
        <Button
          title="Скачать график PDF"
          color="btn-blue"
          disabled={!periods.id || action.busy}
          onClick={() =>
            action.run(() =>
              download(
                `/exports/schedule/${periods.id}.pdf?signatory=${encodeURIComponent(signatory)}`,
                "schedule.pdf",
              ),
            )
          }
        />
      </div>
    </Page>
  );
}
