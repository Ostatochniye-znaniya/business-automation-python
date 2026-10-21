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
    body.setAttribute("aria-busy", String(text === "Загрузка…"));
  }
  function rows(items) {
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
    let canEdit = false;
    const makeInput = (value, type) => {
      const input = document.createElement("input");
      input.className = "field__input access-editor";
      input.type = type || "text";
      if (type === "checkbox") input.checked = Boolean(value);
      else input.value = value || "";
      return input;
    };
    const makeRole = value => {
      const select = document.createElement("select");
      select.className = "field__input access-editor";
      Object.entries(roles).forEach(([key, title]) => select.add(new Option(title, key)));
      select.value = value;
      return select;
    };
    const renderUsers = filtered => {
      body.replaceChildren();
      filtered.forEach(user => {
        const row = document.createElement("tr");
        [user.full_name, user.email || "—", roles[user.role] || user.role,
          user.is_active ? "Активен" : "Отключён"].forEach(value => {
          const cell = document.createElement("td");
          cell.textContent = value;
          row.append(cell);
        });
        const actions = document.createElement("td");
        if (canEdit) {
          const edit = document.createElement("button");
          edit.className = "button";
          edit.type = "button";
          edit.textContent = "Изменить";
          edit.addEventListener("click", () => {
            const name = makeInput(user.full_name);
            const email = makeInput(user.email);
            const userRole = makeRole(user.role);
            const active = makeInput(user.is_active, "checkbox");
            [name, email, userRole, active].forEach((input, index) => {
              const cell = row.children[index];
              cell.replaceChildren(input);
            });
            actions.replaceChildren();
            const save = document.createElement("button");
            save.className = "button button--primary";
            save.type = "button";
            save.textContent = "Сохранить";
            save.addEventListener("click", async () => {
              save.disabled = true;
              try {
                const updated = await apiPut(`/users/${encodeURIComponent(user.id)}`, {
                  full_name: name.value.trim(),
                  email: email.value.trim() || null,
                  is_active: active.checked,
                  role: userRole.value,
                });
                Object.assign(user, updated);
                message("Данные пользователя сохранены.");
                filter();
              } catch (error) {
                message(`Не удалось сохранить данные: ${error.message}`, true);
                save.disabled = false;
              }
            });
            actions.append(save);
          });
          actions.append(edit);
        } else {
          actions.textContent = "Только просмотр";
        }
        row.append(actions);
        body.append(row);
      });
    };
    const filter = () => {
      if (!loaded) return;
      const query = search.value.trim().toLocaleLowerCase("ru-RU");
      const filtered = users.filter(user => (!role.value || role.value === user.role) &&
        `${user.full_name} ${user.email || ""}`.toLocaleLowerCase("ru-RU").includes(query));
      renderUsers(filtered);
      message(filtered.length ? `Найдено пользователей: ${filtered.length}` : "Пользователи не найдены.");
    };
    reload = () => run(async current => {
      loaded = false;
      const [data, actor] = await Promise.all([
        apiGetAll("/users"),
        apiGet("/users/me").catch(() => null),
      ]);
      if (!current()) return;
      users = data;
      canEdit = Boolean(actor && actor.is_active && ["ADMIN", "LPR"].includes(actor.role));
      loaded = true;
      filter();
    });
    search.addEventListener("input", filter);
    role.addEventListener("change", filter);
  } else if (page === "periods") {
    const labels = { DRAFT: "Черновик", OPEN: "Открыт", CLOSED: "Завершён" };
    const date = value => new Date(`${value}T12:00:00`).toLocaleDateString("ru-RU");
    reload = () => run(async current => {
      const data = await apiGetAll("/periods");
      if (!current()) return;
      rows(data.map(period => [period.name, period.academic_year, period.semester === 1 ? "Осень" : "Весна",
        date(period.start_date), date(period.end_date), labels[period.status] || period.status]));
      message(data.length ? `Периодов тестирования: ${data.length}` : "Периоды тестирования пока не добавлены.");
    });
  }
  if (reload) reload();
})();
