(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const status = $("status");
  const roles = {
    ADMIN: "Администратор",
    LPR: "ЛПР",
    DEPARTMENT_HEAD: "Руководитель факультета",
    DEPARTMENT_RESPONSIBLE: "Ответственный факультета",
    CHAIR_HEAD: "Заведующий кафедрой",
    TEACHER: "Преподаватель",
    GUEST: "Гость",
  };
  const labels = {
    PROPOSED: "Ожидает согласования",
    AGREED: "Согласовано",
    REJECTED: "Отклонено",
    PLANNED: "Запланировано",
    IN_PROGRESS: "Идёт проверка",
    COMPLETED: "Завершено",
    CANCELLED: "Отменено",
    DRAFT: "Черновик",
    SUBMITTED: "На проверке",
    APPROVED: "Принято",
    MISSING: "Не сдано",
    PENDING: "Ожидание",
    COMPLETE: "Всё сдано",
  };
  const catalogs = {};
  const sourceCatalogs = {};
  let actor,
    periods = [],
    tests = [],
    activeReport = null,
    revision = 0,
    rosterRevision = 0;
  const name = (catalog, id) =>
    (catalogs[catalog] || []).find(
      (row) => Number(row[0]) === Number(id),
    )?.[1] || `№${id}`;
  function message(text, error = false) {
    status.textContent = text;
    status.dataset.error = String(error);
  }
  async function action(work) {
    try {
      message("Выполняется…");
      await work();
      if (status.textContent === "Выполняется…") message("Готово.");
    } catch (error) {
      message(error.message, true);
    }
  }
  function fill(form, data) {
    for (const [key, value] of Object.entries(data))
      if (form.elements.namedItem(key))
        form.elements.namedItem(key).value = value ?? "";
  }
  function data(form) {
    return Object.fromEntries(new FormData(form));
  }
  function selectOptions(select, items, placeholder = "Выберите…") {
    const previous = select.value;
    select.replaceChildren(new Option(placeholder, ""));
    items.forEach(([value, text]) => select.add(new Option(text, value)));
    if (items.some(([value]) => String(value) === previous))
      select.value = previous;
  }
  function catalog(key, items) {
    catalogs[key] = items;
    document
      .querySelectorAll(`[data-catalog="${key}"]`)
      .forEach((select) => selectOptions(select, items));
  }
  function button(text, work) {
    const element = document.createElement("button");
    element.type = "button";
    element.className = "button";
    element.textContent = text;
    element.addEventListener("click", () => action(work));
    return element;
  }
  function table(id, rows) {
    $(id).replaceChildren(
      ...rows.map((values) => {
        const tr = document.createElement("tr");
        values.forEach((value) => {
          const td = document.createElement("td");
          if (value instanceof Node) td.append(value);
          else td.textContent = value ?? "—";
          tr.append(td);
        });
        return tr;
      }),
    );
  }
  function submit(id, work) {
    $(id).addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.submitter;
      if (button) button.disabled = true;
      await action(() => work(data(event.target), event.target));
      if (button) button.disabled = false;
    });
  }
  function period() {
    if (!$("period").value) throw new Error("Выберите период.");
    return Number($("period").value);
  }
  function resultTest() {
    if (!$("result-test").value) throw new Error("Выберите проверку.");
    return Number($("result-test").value);
  }
  async function download(path) {
    const response = await fetch(API_BASE + path, {
      credentials: "same-origin",
    });
    if (!response.ok)
      throw new Error(
        (await response.json()).detail || "Не удалось скачать документ",
      );
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download =
      response.headers
        .get("content-disposition")
        ?.match(/filename="?([^";]+)/)?.[1] || "document";
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function loadTests() {
    const ticket = ++revision;
    resetRoster();
    const result = await apiGetAll(`/workflow/testing?period_id=${period()}`);
    if (ticket !== revision) return;
    tests = result.filter(
      (test) => actor.role !== "TEACHER" || test.teacher_id === actor.id,
    );
    if (
      ["ADMIN", "LPR", "CHAIR_HEAD", "DEPARTMENT_RESPONSIBLE"].includes(
        actor.role,
      )
    ) {
      const groups = await apiGet(
        `/workflow/eligible-groups?period_id=${period()}`,
      );
      if (ticket !== revision) return;
      catalog(
        "eligibleGroups",
        groups.map((group) => [group.id, group.name]),
      );
    }
    catalog(
      "tests",
      tests
        .filter((test) => test.status !== "CANCELLED")
        .map((test) => [
          test.id,
          `${name("groups", test.group_id)} — ${name("disciplines", test.discipline_id)}`,
        ]),
    );
    table(
      "test-rows",
      tests.map((test) => [
        name("groups", test.group_id),
        name("disciplines", test.discipline_id),
        test.teacher_id ? name("teachers", test.teacher_id) : "Не назначен",
        test.scheduled_at
          ? new Date(test.scheduled_at + "Z").toLocaleString("ru-RU", {
              timeZone: "Europe/Moscow",
            })
          : "Не назначено",
        labels[test.agreement_status],
        labels[test.status],
      ]),
    );
    const selected = periods.find((item) => item.id === period());
    if (selected) fill($("period-form"), selected);
    resetRoster();
  }
  function resetRoster() {
    rosterRevision++;
    activeReport = null;
    $("result-rows").replaceChildren();
    fill($("report-metadata"), { previous_teacher_name: "" });
    $("report-state").textContent = "Выберите проверку и откройте ведомость.";
  }
  async function loadReports(testId = resultTest(), ticket = rosterRevision) {
    const reports = await apiGetAll(`/reports?knowledge_test_id=${testId}`);
    if (ticket !== rosterRevision || testId !== resultTest()) return;
    activeReport = reports[0] || null;
    fill($("report-metadata"), {
      previous_teacher_name: activeReport?.previous_teacher_name || "",
    });
    $("report-state").textContent = activeReport
      ? `Электронная версия: ${labels[activeReport.electronic_status] || "—"}. Бумажная версия: ${labels[activeReport.paper_status] || "—"}. ${activeReport.electronic_comment || ""} ${activeReport.paper_comment || ""}`
      : "Карточка отчёта пока не создана.";
  }
  async function roster() {
    const testId = resultTest();
    const ticket = ++rosterRevision;
    const [students, results] = await Promise.all([
      apiGet(`/workflow/testing/${testId}/roster`),
      apiGetAll(`/results?knowledge_test_id=${testId}`),
    ]);
    if (ticket !== rosterRevision || testId !== resultTest()) return;
    table(
      "result-rows",
      students.map((student) => {
        const existing = results.find(
          (result) => result.student_id === student.id,
        );
        const intermediate = document.createElement("input");
        intermediate.type = "number";
        intermediate.step = "any";
        intermediate.value = existing?.intermediate_result ?? "";
        intermediate.setAttribute(
          "aria-label",
          `Промежуточная аттестация: ${student.full_name}`,
        );
        const score = document.createElement("input");
        score.type = "number";
        score.step = "any";
        score.value = existing?.testing_result ?? "";
        score.setAttribute("aria-label", `Результат: ${student.full_name}`);
        const participation = document.createElement("select");
        [
          ["PASSED", "Прошёл тестирование"],
          ["ABSENT", "Не явился"],
          ["NOT_ADMITTED", "Не допущен"],
        ].forEach(([value, title]) =>
          participation.add(new Option(title, value)),
        );
        participation.value = existing?.participation_status || "PASSED";
        return [
          student.full_name,
          intermediate,
          participation,
          score,
          button("Сохранить", async () => {
            await request("PUT", "/results", {
              knowledge_test_id: testId,
              student_id: student.id,
              participation_status: participation.value,
              intermediate_result:
                intermediate.value === "" ? null : Number(intermediate.value),
              testing_result: score.value === "" ? null : Number(score.value),
            });
          }),
        ];
      }),
    );
    await loadReports(testId, ticket);
  }
  async function reviewQueue() {
    const query = new URLSearchParams({ period_id: period() });
    for (const [id, key] of [
      ["review-faculty", "faculty_id"],
      ["review-group", "group_id"],
      ["review-discipline", "discipline_id"],
    ])
      if ($(id).value) query.set(key, $(id).value);
    const reports = await apiGetAll("/report-workflow?" + query);
    selectOptions(
      $("review-report"),
      reports.map((report) => [report.id, `Отчёт №${report.id}`]),
    );
    table(
      "review-rows",
      reports.map((report) => [
        report.id,
        report.knowledge_test_id,
        labels[report.electronic_status],
        report.electronic_comment,
        labels[report.paper_status],
        labels[report.final_status],
        button("Скачать", () => download(`/report-workflow/${report.id}/file`)),
      ]),
    );
    message(
      reports.length
        ? `Найдено отчётов: ${reports.length}`
        : "Отчётов по выбранным условиям нет.",
    );
  }
  async function users() {
    const records = await apiGetAll("/administration/users");
    table(
      "user-rows",
      records.map((user) => [
        user.full_name,
        roles[user.role],
        user.department_id ? name("departments", user.department_id) : "—",
        button("Изменить", async () => fill($("user-form"), user)),
      ]),
    );
    const imports = await apiGet("/administration/imports");
    $("import-status").textContent = imports.length
      ? `Последний импорт: ${imports[0].status}, обработано ${imports[0].records_processed}, ${imports[0].errors.join("; ")}`
      : "Импорт ещё не выполнялся.";
  }
  async function requests() {
    const records = await apiGetAll("/administration/access-requests");
    table(
      "request-rows",
      records.map((record) => {
        const actions = document.createElement("div");
        if (record.status === "PENDING")
          for (const [approved, label] of [
            [true, "Одобрить"],
            [false, "Отклонить"],
          ])
            actions.append(
              button(label, async () => {
                await request(
                  "PUT",
                  `/administration/access-requests/${record.id}`,
                  { approved },
                );
                await requests();
              }),
            );
        return [
          record.user_id,
          roles[record.requested_role],
          record.reason,
          labels[record.status] || record.status,
          actions,
        ];
      }),
    );
  }
  async function departments() {
    const records = await apiGet("/department-management");
    table(
      "department-rows",
      records.map((row) => {
        const actions = document.createElement("div");
        actions.append(
          button("Изменить", async () => fill($("department-form"), row)),
          button("Удалить", async () => {
            if (!confirm(`Удалить подразделение «${row.name}»?`)) return;
            await request("DELETE", `/department-management/${row.id}`);
            await departments();
          }),
        );
        return [
          row.name,
          row.parent_id ? name("departments", row.parent_id) : "—",
          row.employee_count,
          actions,
        ];
      }),
    );
  }
  function tab(id) {
    document
      .querySelectorAll(".workflow-panel")
      .forEach((panel) => (panel.hidden = panel.id !== id));
    document
      .querySelectorAll("[data-tab]")
      .forEach((button) =>
        button.setAttribute("aria-current", String(button.dataset.tab === id)),
      );
  }
  document
    .querySelectorAll("[data-tab]")
    .forEach((button) =>
      button.addEventListener("click", () => tab(button.dataset.tab)),
    );
  $("period").addEventListener("change", () => action(loadTests));
  $("result-test").addEventListener("change", resetRoster);
  $("refresh").addEventListener("click", () => action(loadTests));
  $("load-roster").addEventListener("click", () => action(roster));
  $("complete").addEventListener("click", () =>
    action(() => apiPost(`/results/complete/${resultTest()}`)),
  );
  $("report-document").addEventListener("click", () =>
    action(() => download(`/exports/report/${resultTest()}.docx`)),
  );
  $("schedule").addEventListener("click", () =>
    action(() =>
      download(
        `/exports/schedule/${period()}.pdf?signatory=${encodeURIComponent($("signatory").value)}`,
      ),
    ),
  );
  $("summary").addEventListener("click", () =>
    action(() => download(`/exports/summary/${period()}.csv`)),
  );
  $("create-report").addEventListener("click", () =>
    action(async () => {
      await apiPost(`/report-workflow/testing/${resultTest()}`);
      await loadReports();
    }),
  );
  $("download-report").addEventListener("click", () =>
    action(() => {
      if (!activeReport) throw new Error("Сначала создайте карточку отчёта.");
      return download(`/report-workflow/${activeReport.id}/file`);
    }),
  );
  $("withdraw").addEventListener("click", () =>
    action(async () => {
      if (!activeReport) throw new Error("Выберите отчёт.");
      await apiPost(`/report-workflow/${activeReport.id}/withdraw`);
      await loadReports();
    }),
  );
  $("delete-report").addEventListener("click", () =>
    action(async () => {
      if (!activeReport) throw new Error("Выберите отчёт.");
      if (!confirm("Удалить черновик отчёта?")) return;
      await request("DELETE", `/report-workflow/${activeReport.id}`);
      await loadReports();
    }),
  );
  $("load-reviews").addEventListener("click", () => action(reviewQueue));
  $("load-users").addEventListener("click", () => action(users));
  $("load-requests").addEventListener("click", () => action(requests));
  $("load-audit").addEventListener("click", () =>
    action(async () => {
      const records = await apiGet("/administration/audit?limit=100");
      table(
        "audit-rows",
        records.map((record) => [
          new Date(record.created_at + "Z").toLocaleString("ru-RU", {
            timeZone: "Europe/Moscow",
          }),
          name("users", record.actor_id),
          record.action,
          record.entity_id ?? "—",
        ]),
      );
    }),
  );
  $("load-departments").addEventListener("click", () => action(departments));
  submit("participation", async (value) => {
    const participates = value.participates === "true";
    await request("PUT", "/workflow/participation", {
      group_id: Number(value.group_id),
      period_id: period(),
      participates,
      discipline_ids: participates
        ? [Number(value.discipline1), Number(value.discipline2)]
        : [],
      reason: value.reason || null,
    });
    await loadTests();
  });
  submit("assignment", async (value) => {
    await request("PUT", `/workflow/testing/${value.test_id}/assignment`, {
      teacher_id: Number(value.teacher_id),
      scheduled_at: new Date(value.scheduled_at + "+03:00").toISOString(),
      room: value.room,
    });
    await loadTests();
  });
  submit("agreement", async (value) => {
    await request("PUT", `/workflow/testing/${value.test_id}/agreement`, {
      approved: value.approved === "true",
      comment: value.comment || null,
    });
    await loadTests();
  });
  submit("upload", async (_, form) => {
    if (!activeReport) throw new Error("Сначала создайте карточку отчёта.");
    await upload(
      `/report-workflow/${activeReport.id}/file`,
      new FormData(form),
    );
    await loadReports();
  });
  submit("report-metadata", async (value) => {
    if (!activeReport) throw new Error("Сначала создайте карточку отчёта.");
    await request("PUT", `/report-workflow/${activeReport.id}/metadata`, value);
  });
  submit("review-form", async (value) => {
    await request(
      "PUT",
      `/report-workflow/${value.report_id}/review/${value.version}`,
      { approved: value.approved === "true", comment: value.comment || null },
    );
    await reviewQueue();
  });
  submit("user-form", async (value) => {
    const id = value.id;
    delete value.id;
    value.department_id = value.department_id
      ? Number(value.department_id)
      : null;
    value.is_active = value.is_active === "true";
    for (const key of ["email", "external_id", "position"])
      value[key] = value[key] || null;
    await request(
      id ? "PUT" : "POST",
      `/administration/users${id ? "/" + id : ""}`,
      value,
    );
    await users();
  });
  submit("period-form", async (value) => {
    const id = value.id;
    delete value.id;
    value.semester = Number(value.semester);
    await request(id ? "PUT" : "POST", `/periods${id ? "/" + id : ""}`, value);
    periods = await apiGetAll("/periods");
    selectOptions(
      $("period"),
      periods.map((row) => [row.id, row.name]),
    );
  });
  submit("department-form", async (value) => {
    const id = value.id;
    delete value.id;
    value.parent_id = value.parent_id ? Number(value.parent_id) : null;
    value.short_name = value.short_name || null;
    await request(
      id ? "PUT" : "POST",
      `/department-management${id ? "/" + id : ""}`,
      value,
    );
    catalog(
      "departments",
      (await apiGetAll("/departments")).map((row) => [row.id, row.name]),
    );
    await departments();
  });
  submit("access-request", async (value) => {
    await apiPost("/administration/access-requests", value);
    message("Заявка передана ЛПР.");
  });
  submit("import-form", async (_, form) => {
    await upload("/administration/imports/employees", new FormData(form));
    await users();
  });
  document.querySelectorAll("[data-editor]").forEach((select) =>
    select.addEventListener("change", () => {
      const row = (sourceCatalogs[select.dataset.editor] || []).find(
        (item) => String(item.id) === select.value,
      );
      if (row) fill(select.form, row);
      else {
        const blank = Object.fromEntries(
          Array.from(select.form.elements)
            .filter((element) => element.name && element.name !== "id")
            .map((element) => [element.name, ""]),
        );
        fill(select.form, blank);
      }
    }),
  );
  async function reloadCatalog(key, path) {
    const rows = await apiGetAll(path);
    sourceCatalogs[key] = rows;
    catalog(
      key,
      rows.map((row) => [row.id, row.name || row.full_name]),
    );
  }
  $("load-students").addEventListener("click", () =>
    action(() => reloadCatalog("students", "/students")),
  );
  submit("program-form", async (value) => {
    const id = value.id;
    delete value.id;
    value.faculty_id = Number(value.faculty_id);
    value.code = value.code || null;
    await request(
      id ? "PUT" : "POST",
      `/catalog/programs${id ? "/" + id : ""}`,
      value,
    );
    await reloadCatalog("programs", "/programs");
  });
  submit("group-form", async (value) => {
    const id = value.id;
    delete value.id;
    for (const key of ["admission_year", "department_id", "study_program_id"])
      value[key] = value[key] ? Number(value[key]) : null;
    value.external_id = value.external_id || null;
    value.period_ids = $("period").value ? [period()] : [];
    await request(
      id ? "PUT" : "POST",
      `/catalog/groups${id ? "/" + id : ""}`,
      value,
    );
    await reloadCatalog("groups", "/groups");
  });
  submit("discipline-form", async (value) => {
    const id = value.id;
    delete value.id;
    value.department_id = value.department_id
      ? Number(value.department_id)
      : null;
    value.external_id = value.external_id || null;
    await request(
      id ? "PUT" : "POST",
      `/disciplines${id ? "/" + id : ""}`,
      value,
    );
    await reloadCatalog("disciplines", "/disciplines");
  });
  submit("student-form", async (value) => {
    const id = value.id;
    delete value.id;
    value.group_id = Number(value.group_id);
    value.external_id = value.external_id || null;
    await request(id ? "PUT" : "POST", `/students${id ? "/" + id : ""}`, value);
    await reloadCatalog("students", "/students");
  });
  async function upload(path, form) {
    const response = await fetch(API_BASE + path, {
      method: "POST",
      body: form,
      credentials: "same-origin",
    });
    const result = await response.json();
    if (!response.ok)
      throw new Error(result.detail || "Не удалось загрузить файл");
    return result;
  }
  for (const form of [$("user-form"), $("period-form"), $("department-form")])
    form.addEventListener("reset", () => {
      setTimeout(() => (form.elements.id.value = ""), 0);
    });
  (async () => {
    try {
      actor = await apiGet("/auth/me");
      $("actor").textContent = `${actor.full_name} — ${roles[actor.role]}`;
      catalog(
        "roles",
        Object.entries(roles).map(([key, title]) => [key, title]),
      );
      if (actor.role === "GUEST") {
        document
          .querySelectorAll(".workflow-panel,.workbench-tabs,.section-filters")
          .forEach((element) => (element.hidden = true));
        $("guest").hidden = false;
        message("Ожидание назначения роли.");
        return;
      }
      const managers = ["ADMIN", "LPR"].includes(actor.role);
      document.querySelectorAll("[data-tab]").forEach((button) => {
        if (
          [
            "review",
            "administration",
            "periods",
            "departments",
            "catalogs",
          ].includes(button.dataset.tab)
        )
          button.hidden = !managers;
      });
      $("participation").hidden =
        actor.role === "TEACHER" || actor.role === "DEPARTMENT_HEAD";
      $("assignment").hidden =
        actor.role === "TEACHER" || actor.role === "DEPARTMENT_HEAD";
      $("agreement").hidden = actor.role !== "TEACHER";
      const [groups, disciplines, employees, units, loadedPeriods] =
        await Promise.all([
          apiGetAll("/groups"),
          apiGetAll("/disciplines"),
          apiGetAll("/users"),
          apiGetAll("/departments"),
          apiGetAll("/periods"),
        ]);
      catalog(
        "groups",
        groups.map((row) => [row.id, row.name]),
      );
      catalog(
        "disciplines",
        disciplines.map((row) => [row.id, row.name]),
      );
      catalog(
        "teachers",
        employees
          .filter((row) => row.role === "TEACHER" && row.is_active)
          .map((row) => [row.id, row.full_name]),
      );
      catalog(
        "users",
        employees.map((row) => [row.id, row.full_name]),
      );
      catalog(
        "departments",
        units.map((row) => [row.id, row.name]),
      );
      sourceCatalogs.groups = groups;
      sourceCatalogs.disciplines = disciplines;
      if (managers) await reloadCatalog("programs", "/programs");
      periods = loadedPeriods;
      selectOptions(
        $("period"),
        periods.map((row) => [row.id, row.name]),
      );
      if (periods.length)
        $("period").value = String(
          (periods.find((row) => row.status === "OPEN") || periods[0]).id,
        );
      if (periods.length) await loadTests();
      tab(actor.role === "TEACHER" ? "results" : "planning");
      message(
        periods.length
          ? "Выберите действие."
          : "Периодов пока нет. ЛПР может создать период.",
      );
    } catch (error) {
      message(
        `Не удалось открыть рабочее место: ${error.message}. Войдите в систему.`,
        true,
      );
    }
  })();
})();
