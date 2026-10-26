"use client";
import { useEffect, useState } from "react";
import Page, { Notice } from "@/components/Page";
import Dropdown from "@/components/dropdown/Dropdown";
import Table from "@/components/table/Table";
import { usePeriod } from "@/lib/hooks";
import { request } from "@/lib/api";
type Summary = {
  id: number;
  name: string;
  groups: { required: number; actual: number };
  disciplines: { required: number; actual: number };
  reports: {
    electronic_submitted: number;
    electronic_with_issues: number;
    paper_submitted: number;
    paper_with_issues: number;
  };
  all_submitted: boolean;
};
export default function StatisticsPage() {
  const periods = usePeriod(),
    [data, setData] = useState<Summary[]>([]),
    [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    if (periods.id)
      request<{ departments: Summary[] }>(
        `/dashboard?period_id=${periods.id}`,
        "GET",
        undefined,
        controller.signal,
      )
        .then((result) => {
          setData(result.departments);
          setError("");
        })
        .catch((reason) => {
          if (!controller.signal.aborted) {
            setData([]);
            setError(reason.message);
          }
        });
    return () => controller.abort();
  }, [periods.id]);
  return (
    <Page title="Статистика">
      <Notice text={error || periods.error} error />
      <div className="filter-grid">
        <Dropdown
          label="Семестр"
          value={periods.id}
          options={periods.data.map((row) => ({
            value: String(row.id),
            label: row.name,
          }))}
          onChange={periods.setId}
        />
      </div>
      <Table
        data={data}
        columns={[
          { header: "Факультет / институт", accessor: "name" },
          {
            header: "Группы · норматив",
            accessor: (row) => row.groups.required,
          },
          { header: "Группы · факт", accessor: (row) => row.groups.actual },
          {
            header: "Дисциплины · норматив",
            accessor: (row) => row.disciplines.required,
          },
          {
            header: "Дисциплины · факт",
            accessor: (row) => row.disciplines.actual,
          },
          {
            header: "Электронные отчёты",
            accessor: (row) => row.reports.electronic_submitted,
          },
          {
            header: "Замечания",
            accessor: (row) => row.reports.electronic_with_issues,
          },
          ...(periods.selected?.paper_reports_required
            ? [
                {
                  header: "Бумажные отчёты",
                  accessor: (row: Summary) => row.reports.paper_submitted,
                },
              ]
            : []),
          {
            header: "Всё сдано",
            accessor: (row) => (row.all_submitted ? "Да" : "Нет"),
          },
        ]}
      />
    </Page>
  );
}
