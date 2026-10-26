(function () {
  const page = document.body.dataset.page;
  if (page === "settings") return;
  const status = document.getElementById("section-status");
  const retry = document.getElementById("section-retry");
  const body = document.getElementById("section-rows");
  const periodSelect = document.getElementById("period");
  let revision = 0;
  let reload;

  function message(text, error = false) {
    status.textContent = text;
    status.dataset.error = String(error);
    retry.hidden = !error;
    if (body) body.setAttribute("aria-busy", String(text === "Загрузка…"));
  }
  function rows(items) {
    if (!body) return;
    body.replaceChildren();
    items.forEach(values => {
      const row = document.createElement("tr");
      values.forEach(value => {
        const cell = document.createElement("td");
        cell.textContent = value ?? "—";
        row.append(cell);
      });
      body.append(row);
    });
  }
  function options(select, items, placeholder) {
    const previous = select.value;
    select.replaceChildren(new Option(placeholder, ""));
    items.forEach(([value, text]) => select.add(new Option(text, String(value))));
    if (items.some(([value]) => String(value) === previous)) select.value = previous;
    select.disabled = !items.length;
  }
  async function run(work) {
    const request = ++revision;
    rows([]);
    message("Загрузка…");
    try {
      await work(() => request === revision);
    } catch (error) {
      if (request === revision) message(`Не удалось загрузить данные: ${error.message}`, true);
    }
  }
  async function loadPeriods() {
    const periods = await apiGetAll("/periods");
    options(periodSelect, periods.map(period => [period.id,
      `${period.name} — ${period.academic_year}, ${period.semester}-й семестр`]), "Выберите период");
    return periods;
  }
  retry.addEventListener("click", () => reload());

  if (page === "home") {
    const dashboard = () => run(async current => {
      if (!periodSelect.value) { message("Выберите период тестирования."); return; }
      const data = await apiGet(`/dashboard?period_id=${encodeURIComponent(periodSelect.value)}`);
      if (!current()) return;
      rows(data.departments.map(department => [department.name,
        `${department.groups.actual ?? "—"} / ${department.groups.required ?? "—"}`,
        `${department.disciplines.actual ?? "—"} / ${department.disciplines.required ?? "—"}`,
        department.reports.electronic_submitted, department.reports.paper_submitted]));
      message(data.departments.length ? "Сводка за выбранный период." : "Подразделения не найдены.");
    });
    reload = () => run(async current => {
      const periods = await loadPeriods();
      if (!current()) return;
      if (!periods.length) { message("Периоды тестирования пока не добавлены."); return; }
      if (!periodSelect.value) periodSelect.value = String(periods[0].id);
      await dashboard();
    });
    periodSelect.addEventListener("change", dashboard);
  } else if (page === "reports") {
    const testingSelect = document.getElementById("testing");
    let groupNames = new Map();
    let disciplineNames = new Map();
    const reports = () => run(async current => {
      if (!testingSelect.value) { message("Выберите тестирование группы."); return; }
      const data = await apiGetAll(`/reports?knowledge_test_id=${encodeURIComponent(testingSelect.value)}`);
      if (!current()) return;
      rows(data.map(report => [report.id, report.electronic_status, report.electronic_comment,
        report.paper_status, report.paper_comment, report.final_status]));
      message(data.length ? `Найдено отчётов: ${data.length}` : "Отчёты для выбранного тестирования пока не добавлены.");
    });
    const tests = () => run(async current => {
      options(testingSelect, [], "Выберите тестирование");
      if (!periodSelect.value) { message("Выберите период тестирования."); return; }
      const data = await apiGetAll(`/testing?period_id=${encodeURIComponent(periodSelect.value)}`);
      if (!current()) return;
      options(testingSelect, data.map(test => [test.id,
        `${groupNames.get(test.group_id) || `Группа №${test.group_id}`} — ${disciplineNames.get(test.discipline_id) || `Дисциплина №${test.discipline_id}`} (№${test.id})`]), "Выберите тестирование");
      message(data.length ? "Выберите тестирование группы." : "В выбранном периоде нет тестирований.");
    });
    reload = () => run(async current => {
      testingSelect.disabled = true;
      const [periods, groups, disciplines] = await Promise.all([loadPeriods(), apiGetAll("/groups"), apiGetAll("/disciplines")]);
      if (!current()) return;
      groupNames = new Map(groups.map(group => [group.id, group.name]));
      disciplineNames = new Map(disciplines.map(discipline => [discipline.id, discipline.name]));
      if (!periods.length) { message("Периоды тестирования пока не добавлены."); return; }
      if (!periodSelect.value) periodSelect.value = String(periods[0].id);
      await tests();
    });
    periodSelect.addEventListener("change", tests);
    testingSelect.addEventListener("change", reports);
  } else if (page === "access") {
    const search = document.getElementById("user-search");
    const role = document.getElementById("user-role");
    const roles = { ADMIN: "Администратор", LPR: "ЛПР", DEPARTMENT_HEAD: "Руководитель подразделения", DEPARTMENT_RESPONSIBLE: "Ответственный подразделения", CHAIR_HEAD: "Заведующий кафедрой", TEACHER: "Преподаватель", GUEST: "Гость" };
    Object.entries(roles).forEach(([value, title]) => role.add(new Option(title, value)));
    let users = [];
    let loaded = false;
    const filter = () => {
      if (!loaded) return;
      const query = search.value.trim().toLocaleLowerCase("ru-RU");
      const filtered = users.filter(user => (!role.value || role.value === user.role) &&
        `${user.full_name} ${user.email || ""}`.toLocaleLowerCase("ru-RU").includes(query));
      rows(filtered.map(user => [user.full_name, user.email, roles[user.role] || user.role, user.is_active ? "Активен" : "Отключён"]));
      message(filtered.length ? `Найдено пользователей: ${filtered.length}` : "Пользователи не найдены.");
    };
    reload = () => run(async current => {
      loaded = false;
      const data = await apiGetAll("/users");
      if (!current()) return;
      users = data;
      loaded = true;
      filter();
    });
    search.addEventListener("input", filter);
    role.addEventListener("change", filter);
  } else if (page === "periods") {
    const semesterFilter = document.getElementById("semester-filter");
    const scheduleDeadlines = document.getElementById("schedule-deadlines");
    const reportDeadlines = document.getElementById("report-deadlines");
    const deadlineGroups = [
      {
        target: scheduleDeadlines,
        items: [
          { id: "student-lists", label: "Формирование списков студентов", range: true },
          { id: "testing-schedules", label: "Формирование графиков тестирования", range: true },
          { id: "surveys", label: "Сроки проведения анкетирования", range: true },
        ],
      },
      {
        target: reportDeadlines,
        items: [
          { id: "electronic-reports", label: "Сдача электронных отчётов до" },
          { id: "paper-reports", label: "Сдача бумажных отчётов до" },
          { id: "summary-report", label: "Подготовка сводного отчёта до" },
        ],
      },
    ];
    let periods = [];
    let selectedPeriod;
    const deadlineValues = new Map();
    const semesterLabel = period => {
      const years = period.academic_year.split("/");
      const year = period.semester === 1 ? years[0] : years[1] || years[0];
      const season = period.semester === 1 ? "Осень" : "Весна";
      return `${season} ${year}`;
    };
    const renderDeadlines = () => {
      const values = deadlineValues.get(selectedPeriod.id) || {};
      deadlineGroups.forEach(group => {
        group.target.replaceChildren();
        group.items.forEach(item => {
          const row = document.createElement("div");
          row.className = "deadline-row";
          const label = document.createElement("span");
          label.className = "deadline-row__label";
          label.textContent = item.label;
          row.append(label);
          const dates = document.createElement("div");
          dates.className = "deadline-row__dates";
          const keys = item.range ? ["start", "end"] : ["date"];
          keys.forEach((key, index) => {
            if (index > 0) {
              const separator = document.createElement("span");
              separator.className = "deadline-row__separator";
              separator.setAttribute("aria-hidden", "true");
              separator.textContent = "—";
              dates.append(separator);
            }
            const input = document.createElement("input");
            input.className = "deadline-date";
            input.type = "date";
            const valueKey = `${item.id}:${key}`;
            input.value = Object.prototype.hasOwnProperty.call(values, valueKey)
              ? values[valueKey]
              : "2025-01-01";
            input.setAttribute("aria-label", `${item.label}: ${key === "start" ? "начало" : key === "end" ? "окончание" : "дата"}`);
            input.addEventListener("change", () => {
              const currentValues = deadlineValues.get(selectedPeriod.id) || {};
              currentValues[`${item.id}:${key}`] = input.value;
              deadlineValues.set(selectedPeriod.id, currentValues);
              document.dispatchEvent(new CustomEvent("testing-period-deadline-changed", {
                detail: {
                  periodId: selectedPeriod.id,
                  semester: selectedPeriod.semester,
                  deadline: item.id,
                  dateType: key,
                  date: input.value,
                },
              }));
              message("Изменение видно только в текущем окне: API сохранения сроков ещё не подключён.");
            });
            dates.append(input);
          });
          row.append(dates);
          group.target.append(row);
        });
      });
    };
    const renderSelectedPeriod = () => {
      selectedPeriod = periods.find(period => String(period.id) === semesterFilter.value);
      deadlineGroups.forEach(group => group.target.replaceChildren());
      if (!selectedPeriod) {
        message("Выберите семестр для настройки сроков.");
        return;
      }
      renderDeadlines();
      message(`Сроки для периода «${selectedPeriod.name}» показаны как демонстрационные; API сохранения ещё не подключён.`);
    };
    semesterFilter.addEventListener("change", renderSelectedPeriod);
    reload = () => run(async current => {
      periods = await apiGetAll("/periods");
      if (!current()) return;
      const previous = semesterFilter.value;
      semesterFilter.replaceChildren(new Option("Выберите семестр", ""));
      periods.forEach(period => {
        semesterFilter.add(new Option(semesterLabel(period), String(period.id)));
      });
      semesterFilter.disabled = !periods.length;
      if (periods.some(period => String(period.id) === previous)) semesterFilter.value = previous;
      else if (periods.length) semesterFilter.value = String(periods[0].id);
      if (periods.length) renderSelectedPeriod();
      else message("Периоды тестирования пока не добавлены.");
    });
  }
  if (reload) reload();
})();
