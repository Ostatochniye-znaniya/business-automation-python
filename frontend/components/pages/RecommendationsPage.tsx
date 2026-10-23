"use client";
import { useState } from "react";
import Page, { Notice } from "@/components/Page";
import Table from "@/components/table/Table";
import Dropdown from "@/components/dropdown/Dropdown";
import Button from "@/components/button/Button";
import { useAction, useList, usePeriod } from "@/lib/hooks";
import { Group, Department } from "@/lib/types";
import { download, getAll, request } from "@/lib/api";
export default function RecommendationsPage() {
  const periods = usePeriod(),
    groups = useList<
      Group & {
        recommendations: {
          group_id: number;
          period_id: number;
          recommended: boolean;
          version: number;
        }[];
      }
    >("/groups/testing-overview"),
    units = useList<Department>("/departments");
  const recommendations = groups.data
    .flatMap((group) => group.recommendations)
    .filter((row) => row.period_id === Number(periods.id));
  const [pending, setPending] = useState<Record<number, boolean>>({}),
    [search, setSearch] = useState(""),
    [history, setHistory] = useState("");
  const action = useAction();
  const selected = (id: number) =>
    pending[id] ??
    recommendations.some((row) => row.group_id === id && row.recommended);
  return (
    <Page title="Списки рекомендуемых групп">
      <Notice text={action.notice} error={action.failed} />
      <Notice text={periods.error || groups.error} error />
      <div className="filter-grid">
        <Dropdown
          label="Семестр"
          options={periods.data.map((row) => ({
            value: String(row.id),
            label: row.name,
          }))}
          value={periods.id}
          onChange={(value) => {
            if (
              Object.keys(pending).length &&
              !confirm("Отменить несохранённый выбор?")
            )
              return;
            periods.setId(value);
            setPending({});
          }}
        />
        <label className="native-field">
          Поиск группы
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
      </div>
      <Table
        data={groups.data.filter((row) =>
          row.name.toLowerCase().includes(search.toLowerCase()),
        )}
        columns={[
          {
            header: "Рекомендована",
            accessor: (row) => (
              <input
                type="checkbox"
                aria-label={`Рекомендовать ${row.name}`}
                checked={selected(row.id)}
                disabled={periods.selected?.status !== "OPEN"}
                onChange={(event) =>
                  setPending({ ...pending, [row.id]: event.target.checked })
                }
              />
            ),
          },
          { header: "Группа", accessor: "name" },
          {
            header: "Подразделение",
            accessor: (row) =>
              units.data.find((unit) => unit.id === row.department_id)?.name ||
              "—",
          },
          {
            header: "",
            accessor: (row) => (
              <Button
                title="История"
                color="btn-blue"
                onClick={() =>
                  action.run(async () => {
                    const changes = await getAll<{
                      changed_by_name: string;
                      changed_at: string;
                      recommended: boolean;
                    }>(
                      `/recommendations/history?group_id=${row.id}&period_id=${periods.id}`,
                    );
                    setHistory(
                      changes
                        .map(
                          (change) =>
                            `${new Date(change.changed_at).toLocaleString("ru-RU")}: ${change.changed_by_name} — ${change.recommended ? "рекомендована" : "не рекомендована"}`,
                        )
                        .join("\n") || "Изменений нет.",
                    );
                  })
                }
              />
            ),
          },
        ]}
      />
      <div className="row-actions">
        <Button
          title="Сохранить рекомендации"
          color="btn-blue"
          disabled={action.busy || !Object.keys(pending).length}
          onClick={() =>
            action.run(async () => {
              await request("/recommendations", "PUT", {
                changes: Object.entries(pending).map(([id, recommended]) => ({
                  group_id: Number(id),
                  period_id: Number(periods.id),
                  recommended,
                  expected_version:
                    recommendations.find((row) => row.group_id === Number(id))
                      ?.version || 0,
                })),
              });
              setPending({});
              groups.reload();
            })
          }
        />
        <Button
          title="Скачать список CSV"
          color="btn-blue"
          disabled={!periods.id}
          onClick={() =>
            action.run(() =>
              download(
                `/recommendations/export?period_id=${periods.id}`,
                "groups.csv",
              ),
            )
          }
        />
      </div>
      {history && <pre className="notice">{history}</pre>}
    </Page>
  );
}
