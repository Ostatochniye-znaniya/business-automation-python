"use client";
import Link from "next/link";
import { useState } from "react";
import Page, { Notice } from "@/components/Page";
import { usePeriod } from "@/lib/hooks";
import styles from "./DeadlineSettingsPage.module.css";

const deadlines = [
  {
    title: "Списки, графики и анкетирование",
    items: [
      { id: "student-lists", label: "Формирование списков студентов", range: true },
      { id: "testing-schedules", label: "Формирование графиков тестирования", range: true },
      { id: "surveys", label: "Сроки проведения анкетирования", range: true },
    ],
  },
  {
    title: "Отчёты",
    items: [
      { id: "electronic-reports", label: "Сдача электронных отчётов до", range: false },
      { id: "paper-reports", label: "Сдача бумажных отчётов до", range: false },
      { id: "summary-report", label: "Подготовка сводного отчёта до", range: false },
    ],
  },
] as const;

type DeadlineValues = Record<number, Record<string, string>>;

function semesterLabel(academicYear: string, semester: number): string {
  const [startYear, endYear] = academicYear.split("/");
  const year = semester === 1 ? startYear : endYear || startYear;
  return `${semester === 1 ? "Осень" : "Весна"} ${year}`;
}

export default function DeadlineSettingsPage() {
  const periods = usePeriod();
  const [values, setValues] = useState<DeadlineValues>({});
  const [notice, setNotice] = useState("");
  const selected = periods.selected;

  function updateDeadline(key: string, value: string) {
    if (!selected) return;
    setValues((current) => ({
      ...current,
      [selected.id]: { ...current[selected.id], [key]: value },
    }));
    setNotice("Изменение отображается только в текущем сеансе: отдельные сроки пока не сохраняются через API.");
  }

  return (
    <Page title="Настройки доступа">
      <Notice text={periods.error} error />
      <section className={styles.card} aria-label="Настройка дат">
        <nav className={styles.tabs} aria-label="Настройки доступа">
          <Link className={styles.tab} href="/access-rights">
            Настройка ролей
          </Link>
          <Link
            className={`${styles.tab} ${styles.activeTab}`}
            href="/lpr/settings/dates"
            aria-current="page"
          >
            Настройка дат
          </Link>
        </nav>
        <label className={styles.semester}>
          <span>Семестр</span>
          <select
            aria-label="Семестр"
            disabled={!periods.data.length}
            value={periods.id}
            onChange={(event) => {
              periods.setId(event.target.value);
              setNotice("");
            }}
          >
            {periods.data.map((period) => (
              <option key={period.id} value={period.id}>
                {semesterLabel(period.academic_year, period.semester)}
              </option>
            ))}
          </select>
        </label>
        <Notice
          text={
            notice ||
            "Даты для проверки макета демонстрационные. Изменения не сохраняются после перезагрузки."
          }
        />
        {periods.loading ? (
          <p className={styles.status} role="status">
            Загрузка семестров…
          </p>
        ) : periods.data.length === 0 ? (
          <p className={styles.status} role="status">
            Семестры пока не добавлены.
          </p>
        ) : !selected ? (
          <p className={styles.status} role="status">
            Выберите семестр для настройки сроков.
          </p>
        ) : (
          <div className={styles.deadlines}>
            {deadlines.map((group) => (
              <section className={styles.group} key={group.title}>
                <h2>{group.title}</h2>
                <div className={styles.rows}>
                  {group.items.map((item) => (
                    <div className={styles.row} key={item.id}>
                      <label
                        className={styles.label}
                        htmlFor={`${item.id}-start`}
                      >
                        {item.label}
                      </label>
                      <div className={styles.dateFields}>
                        <input
                          id={`${item.id}-start`}
                          aria-label={`${item.label}: ${item.range ? "начало" : "дата"}`}
                          type="date"
                          value={
                            values[selected.id]?.[`${item.id}:start`] ??
                            "2025-01-01"
                          }
                          onChange={(event) =>
                            updateDeadline(`${item.id}:start`, event.target.value)
                          }
                        />
                        {item.range && (
                          <>
                            <span aria-hidden="true">—</span>
                            <input
                              aria-label={`${item.label}: окончание`}
                              type="date"
                              value={
                                values[selected.id]?.[`${item.id}:end`] ??
                                "2025-01-01"
                              }
                              onChange={(event) =>
                                updateDeadline(`${item.id}:end`, event.target.value)
                              }
                            />
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </section>
    </Page>
  );
}
