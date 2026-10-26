"use client";
import { useEffect, useState } from "react";
import Button from "@/components/button/Button";
import { Notice } from "@/components/Page";
import { getAll, request } from "@/lib/api";
import { useAction } from "@/lib/hooks";
type Row = {
  student_id: number;
  full_name: string;
  intermediate_result: string;
  testing_result: string;
  participation_status: string;
};
export default function ResultsEditor({
  testId,
  onSaved,
}: {
  testId: number;
  onSaved: () => void;
}) {
  const [rows, setRows] = useState<Row[]>([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const action = useAction();
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      request<{ id: number; full_name: string }[]>(
        `/workflow/testing/${testId}/roster`,
        "GET",
        undefined,
        controller.signal,
      ),
      getAll<{
        student_id: number;
        intermediate_result: number | null;
        testing_result: number | null;
        participation_status: string;
      }>(`/results?knowledge_test_id=${testId}`, controller.signal),
    ])
      .then(([students, results]) => {
        setRows(
          students.map((student) => {
            const result = results.find((row) => row.student_id === student.id);
            return {
              student_id: student.id,
              full_name: student.full_name,
              intermediate_result: String(result?.intermediate_result ?? ""),
              testing_result: String(result?.testing_result ?? ""),
              participation_status: result?.participation_status || "PASSED",
            };
          }),
        );
        setLoading(false);
      })
      .catch((reason) => {
        if (!controller.signal.aborted) {
          setError(reason.message);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [testId]);
  function change(index: number, key: keyof Row, value: string) {
    setRows((current) =>
      current.map((row, i) =>
        i === index
          ? {
              ...row,
              [key]: value,
              ...(key === "participation_status" && value !== "PASSED"
                ? { testing_result: "" }
                : {}),
            }
          : row,
      ),
    );
  }
  async function save(complete = false) {
    for (const row of rows)
      await request("/results", "PUT", {
        knowledge_test_id: testId,
        student_id: row.student_id,
        participation_status: row.participation_status,
        intermediate_result:
          row.intermediate_result === ""
            ? null
            : Number(row.intermediate_result),
        testing_result:
          row.testing_result === "" ? null : Number(row.testing_result),
      });
    if (complete) await request(`/results/complete/${testId}`, "POST");
    onSaved();
  }
  return (
    <>
      <Notice text={error || action.notice} error={!!error || action.failed} />
      {loading ? (
        <p>Загрузка ведомости…</p>
      ) : (
        <>
          <div className="table-wrapper">
            <table className="table-container">
              <thead>
                <tr>
                  <th>Студент</th>
                  <th>Промежуточная аттестация</th>
                  <th>Участие</th>
                  <th>Результат тестирования</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr key={row.student_id}>
                    <td>{row.full_name}</td>
                    <td>
                      <input
                        aria-label={`Промежуточная аттестация ${row.full_name}`}
                        type="number"
                        step="any"
                        value={row.intermediate_result}
                        onChange={(event) =>
                          change(
                            index,
                            "intermediate_result",
                            event.target.value,
                          )
                        }
                      />
                    </td>
                    <td>
                      <select
                        aria-label={`Участие ${row.full_name}`}
                        value={row.participation_status}
                        onChange={(event) =>
                          change(
                            index,
                            "participation_status",
                            event.target.value,
                          )
                        }
                      >
                        <option value="PASSED">Прошёл тестирование</option>
                        <option value="ABSENT">Не явился</option>
                        <option value="NOT_ADMITTED">Не допущен</option>
                      </select>
                    </td>
                    <td>
                      <input
                        aria-label={`Результат ${row.full_name}`}
                        type="number"
                        step="any"
                        disabled={row.participation_status !== "PASSED"}
                        value={row.testing_result}
                        onChange={(event) =>
                          change(index, "testing_result", event.target.value)
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row-actions">
            <Button
              title="Сохранить результаты"
              color="btn-blue"
              disabled={action.busy || !rows.length}
              onClick={() => action.run(() => save())}
            />
            <Button
              title="Завершить ведомость"
              color="btn-green"
              disabled={action.busy || !rows.length}
              onClick={() => action.run(() => save(true))}
            />
          </div>
        </>
      )}
    </>
  );
}
