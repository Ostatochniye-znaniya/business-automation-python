(function () {
  // Отчёты проверки живут в API, сводные отчёты пока хранятся только на странице.
  const STATUS_OPTIONS = ["Не выбрано", "Сдан", "Принят", "На проверке", "Получен", "Не сдан", "На доработке", "В работе"];
  const ACCEPTED_ELECTRONIC = new Set(["Сдан", "Принят"]);
  const ACCEPTED_PAPER = new Set(["Сдан", "Получен"]);
  const PAGE_SIZE = 4;

  const checkPanel = document.getElementById("check-panel");
  const summaryPanel = document.getElementById("summary-panel");
  const checkTab = document.getElementById("check-tab");
  const summaryTab = document.getElementById("summary-tab");

  const status = document.getElementById("reports-status");
  const retry = document.getElementById("reports-retry");
  const body = document.getElementById("reports-rows");
  const periodSelect = document.getElementById("period");
  const testingSelect = document.getElementById("testing");
  const electronicFilter = document.getElementById("electronic-filter");
  const paperFilter = document.getElementById("paper-filter");
  const statistics = document.getElementById("reports-statistics");
  const statisticsElectronic = document.getElementById("statistics-electronic");
  const statisticsPaper = document.getElementById("statistics-paper");
  const pagination = document.getElementById("reports-pagination");

  const createSummaryButton = document.getElementById("create-summary");
  const summarySearch = document.getElementById("summary-search");
  const summaryList = document.getElementById("summary-list");
  const summaryEmpty = document.getElementById("summary-empty");

  let revision = 0;
  let reports = [];
  let tests = [];
  let groupNames = new Map();
  let disciplineNames = new Map();
  let expandedId = null;
  let currentPage = 1;
  let selectedSummaryId = null;

  function message(text, error = false) {
    status.textContent = text;
    status.dataset.error = String(error);
    retry.hidden = !error;
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

  retry.addEventListener("click", loadAll);

  function fillStatusFilters() {
    STATUS_OPTIONS.forEach(value => {
      electronicFilter.add(new Option(value, value));
      paperFilter.add(new Option(value, value));
    });
  }

  function visibleReports() {
    // Пустое значение фильтра равнозначно «Не выбрано».
    return reports.filter(report => {
      const electronicMatches = !electronicFilter.value || electronicFilter.value === "Не выбрано"
        || report.electronic_status === electronicFilter.value;
      const paperMatches = !paperFilter.value || paperFilter.value === "Не выбрано"
        || report.paper_status === paperFilter.value;
      return electronicMatches && paperMatches;
    });
  }

  function paginationWindow(totalPages) {
    if (totalPages <= 3) return Array.from({ length: totalPages }, (_, index) => index + 1);
    if (currentPage < 3) return [1, 2, 3];
    if (currentPage >= totalPages - 2) return [totalPages - 2, totalPages - 1, totalPages];
    return [currentPage, currentPage + 1, currentPage + 2];
  }

  function paginationButton(label, target, { current = false, disabled = false, dots = false } = {}) {
    if (dots) {
      const span = document.createElement("span");
      span.textContent = "…";
      span.setAttribute("aria-hidden", "true");
      return span;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    if (current) { button.classList.add("is-current"); button.setAttribute("aria-current", "page"); }
    button.disabled = disabled;
    button.addEventListener("click", () => {
      currentPage = target;
      renderCheck();
    });
    return button;
  }

  function renderPagination(totalPages) {
    pagination.replaceChildren();
    if (totalPages <= 1) { pagination.hidden = true; return; }
    pagination.hidden = false;
    const window = paginationWindow(totalPages);
    pagination.append(paginationButton("‹", currentPage - 1, { disabled: currentPage === 1 }));
    if (window[0] !== 1) pagination.append(paginationButton("1", 1));
    if (window[0] > 2) pagination.append(paginationButton("", 0, { dots: true }));
    window.forEach(page => pagination.append(paginationButton(String(page), page, { current: page === currentPage })));
    if (window[window.length - 1] !== totalPages) {
      pagination.append(paginationButton("", 0, { dots: true }));
      pagination.append(paginationButton(String(totalPages), totalPages));
    }
    pagination.append(paginationButton("›", currentPage + 1, { disabled: currentPage === totalPages }));
  }

  function renderScores(report) {
    const main = document.createElement("tr");
    const test = tests.find(item => String(item.id) === testingSelect.value);
    const labels = test
      ? [groupNames.get(test.group_id) || `Группа №${test.group_id}`,
         disciplineNames.get(test.discipline_id) || `Дисциплина №${test.discipline_id}`]
      : [`Тестирование №${report.knowledge_test_id}`, "—"];
    const groupCell = document.createElement("td");
    const disciplineCell = document.createElement("td");
    const electronicCell = document.createElement("td");
    const paperCell = document.createElement("td");
    groupCell.textContent = labels[0];
    disciplineCell.textContent = labels[1];
    electronicCell.textContent = report.electronic_status ?? "—";
    paperCell.textContent = report.paper_status ?? "—";
    main.append(groupCell, disciplineCell, electronicCell, paperCell);
    const actionCell = document.createElement("td");
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "reports-details-toggle";
    toggle.setAttribute("aria-expanded", String(expandedId === report.id));
    toggle.textContent = expandedId === report.id ? "Свернуть" : "Подробнее";
    toggle.addEventListener("click", () => {
      expandedId = expandedId === report.id ? null : report.id;
      renderCheck();
    });
    actionCell.append(toggle);
    main.append(actionCell);
    return main;
  }

  function renderScoresDetails(report) {
    const tr = document.createElement("tr");
    const cell = document.createElement("td");
    const details = document.createElement("div");
    details.className = "reports-details";
    const list = document.createElement("dl");
    const entry = (term, definition) => {
      if (!definition) return;
      const item = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = term;
      dd.textContent = definition;
      item.append(dt, dd);
      list.append(item);
    };
    entry("Электронный отчёт: комментарий", report.electronic_comment);
    entry("Бумажный отчёт: комментарий", report.paper_comment);
    entry("Итоговый статус", report.final_status);
    entry("Электронный отчёт: файл", report.electronic_file_key ? report.electronic_file_key.split("/").pop() : null);
    const actions = document.createElement("div");
    actions.className = "reports-details-actions";
    const accept = document.createElement("button");
    accept.type = "button";
    accept.className = "button button--accept";
    accept.textContent = "Принять";
    accept.addEventListener("click", () => {
      report.electronic_status = "Принят";
      report.final_status = "Принят";
      renderCheck();
    });
    const reject = document.createElement("button");
    reject.type = "button";
    reject.className = "button button--return";
    reject.textContent = "Вернуть на доработку";
    reject.addEventListener("click", () => {
      report.electronic_status = "На доработке";
      report.final_status = "В работе";
      renderCheck();
    });
    actions.append(accept, reject);
    details.append(list, actions);
    cell.append(details);
    tr.append(cell);
    return tr;
  }

  function renderCheck() {
    const filtered = visibleReports();
    const page = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
    body.replaceChildren();
    page.forEach(report => body.append(renderScores(report), renderScoresDetails(report)));

    if (testingSelect.value && filtered.length) {
      const acceptedElectronic = filtered.filter(report => ACCEPTED_ELECTRONIC.has(report.electronic_status)).length;
      const acceptedPaper = filtered.filter(report => ACCEPTED_PAPER.has(report.paper_status)).length;
      statisticsElectronic.textContent = `принято электронных: ${acceptedElectronic} из ${filtered.length},`;
      statisticsPaper.textContent = `получено бумажных: ${acceptedPaper} из ${filtered.length}.`;
      statistics.hidden = false;
    } else {
      statistics.hidden = true;
    }

    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;
    renderPagination(totalPages);

    if (!testingSelect.value) message("Выберите тестирование группы.");
    else if (!reports.length) message("Отчёты для выбранного тестирования пока не добавлены.");
    else if (!filtered.length) message("Отчётов с выбранными статусами нет.");
    else message(`Найдено отчётов: ${filtered.length}`);
  }

  function loadTestingOptions() {
    options(testingSelect, tests.map(test => [test.id,
      `${groupNames.get(test.group_id) || `Группа №${test.group_id}`} — ${disciplineNames.get(test.discipline_id) || `Дисциплина №${test.discipline_id}`} (№${test.id})`]), "Выберите тестирование");
    if (!testingSelect.children.length) message("В выбранном периоде нет тестирований.");
    else if (!testingSelect.value) message("Выберите тестирование группы.");
  }

  function clearReports(statusText) {
    reports = [];
    expandedId = null;
    currentPage = 1;
    renderCheck();
    if (statusText) message(statusText);
  }

  function loadReports() {
    return run(async current => {
      if (!testingSelect.value) { clearReports("Выберите тестирование группы."); return; }
      const data = await apiGetAll(`/reports?knowledge_test_id=${encodeURIComponent(testingSelect.value)}`);
      if (!current()) return;
      reports = data;
      expandedId = null;
      currentPage = 1;
      renderCheck();
    });
  }

  function loadTesting() {
    return run(async current => {
      testingSelect.replaceChildren(new Option("Выберите тестирование", ""));
      testingSelect.disabled = true;
      clearReports(!periodSelect.value ? "Выберите период тестирования." : "Загрузка…");
      if (!periodSelect.value) return;
      const data = await apiGetAll(`/testing?period_id=${encodeURIComponent(periodSelect.value)}`);
      if (!current()) return;
      tests = data;
      loadTestingOptions();
      clearReports();
    });
  }

  function loadAll() {
    return run(async current => {
      testingSelect.replaceChildren(new Option("Выберите тестирование", ""));
      testingSelect.disabled = true;
      const [periods, groups, disciplines] = await Promise.all([loadPeriods(), apiGetAll("/groups"), apiGetAll("/disciplines")]);
      if (!current()) return;
      groupNames = new Map(groups.map(group => [group.id, group.name]));
      disciplineNames = new Map(disciplines.map(discipline => [discipline.id, discipline.name]));
      if (!periods.length) { clearReports("Периоды тестирования пока не добавлены."); testingSelect.disabled = true; return; }
      if (!periodSelect.value) periodSelect.value = String(periods[0].id);
      tests = await apiGetAll(`/testing?period_id=${encodeURIComponent(periodSelect.value)}`);
      if (!current()) return;
      loadTestingOptions();
      clearReports();
    });
  }

  function switchPanel(target) {
    const check = target === "check";
    checkPanel.hidden = !check;
    summaryPanel.hidden = check;
    checkTab.classList.toggle("is-active", check);
    summaryTab.classList.toggle("is-active", !check);
    checkTab.setAttribute("aria-selected", String(check));
    summaryTab.setAttribute("aria-selected", String(!check));
  }

  function renderSummary() {
    const query = summarySearch.value.trim().toLocaleLowerCase("ru-RU");
    const visible = summary.filter(item => item.title.toLocaleLowerCase("ru-RU").includes(query));
    summaryList.replaceChildren();
    visible.forEach(item => {
      const element = document.createElement("button");
      element.type = "button";
      element.className = "reports-summary-item";
      element.textContent = item.title;
      if (item.id === selectedSummaryId) element.classList.add("is-selected");
      element.addEventListener("click", () => {
        selectedSummaryId = selectedSummaryId === item.id ? null : item.id;
        renderSummary();
      });
      summaryList.append(element);
    });
    summaryEmpty.hidden = visible.length > 0;
  }

  // сводный список без API: стартовый набор повторяет макет, новые добавляются локально
  let summary = Array.from({ length: 13 }, (_, index) => ({
    id: index + 1,
    number: 100 - index,
    title: `Сводный отчет №${String(100 - index).padStart(3, "0")} по результатам Проверки, весна 2024 от 05.05.2024`,
  }));

  createSummaryButton.addEventListener("click", () => {
    const nextNumber = summary.reduce((max, item) => Math.max(max, item.number), 99) + 1;
    const createdAt = new Intl.DateTimeFormat("ru-RU").format(new Date());
    summary.unshift({ id: Date.now(), number: nextNumber, title: `Сводный отчет №${nextNumber} по результатам Проверки от ${createdAt}` });
    selectedSummaryId = null;
    renderSummary();
  });

  summarySearch.addEventListener("input", renderSummary);
  electronicFilter.addEventListener("change", () => { currentPage = 1; expandedId = null; renderCheck(); });
  paperFilter.addEventListener("change", () => { currentPage = 1; expandedId = null; renderCheck(); });
  periodSelect.addEventListener("change", loadTesting);
  testingSelect.addEventListener("change", loadReports);
  checkTab.addEventListener("click", () => switchPanel("check"));
  summaryTab.addEventListener("click", () => switchPanel("summary"));

  fillStatusFilters();
  switchPanel("check");
  renderSummary();
  loadAll();
})();
