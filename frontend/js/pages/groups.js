const facultySelect = document.getElementById("faculty");
const programSelect = document.getElementById("program");
const yearSelect = document.getElementById("academic-year");
const semesterSelect = document.getElementById("semester");
const groupsBody = document.getElementById("groups-body");
const groupsStatus = document.getElementById("groups-status");
const retryButton = document.getElementById("retry");
let programs = [];
let periods = [];
let disciplines = [];
let groupsRequest = 0;
let referencesReady = false;
let loadedGroups = [];
let canManageRecommendations = false;
let savingRecommendations = false;
let savingDisciplines = false;
const pendingRecommendations = new Map();
const listPeriodSelect = document.getElementById("list-period");
const recommendationStatus = document.getElementById("recommendation-status");
const disciplineSelect = document.getElementById("selected-disciplines");

function setOptions(select, entries, placeholder) {
  const previous = select.value;
  select.replaceChildren(new Option(placeholder, ""));
  entries.forEach(([value, label]) => select.add(new Option(label, String(value))));
  if (entries.some(([value]) => String(value) === previous)) select.value = previous;
}

function setDisciplineOptions() {
  const selected = new Set(Array.from(disciplineSelect.selectedOptions || []).map(option => option.value));
  disciplineSelect.replaceChildren();
  disciplines.forEach(discipline => {
    const option = new Option(discipline.name, String(discipline.id));
    option.selected = selected.has(option.value);
    disciplineSelect.add(option);
  });
}

function updatePrograms() {
  const available = programs.filter(program => !facultySelect.value ||
    String(program.faculty_id) === facultySelect.value);
  setOptions(programSelect, available.map(program => [program.id,
    [program.code, program.name].filter(Boolean).join(" — ")]), "Все направления");
}

function updateSemesters() {
  const available = periods.filter(period => !yearSelect.value ||
    period.academic_year === yearSelect.value);
  const semesters = [...new Set(available.map(period => period.semester))].sort();
  setOptions(semesterSelect, semesters.map(value => [value, `${value}-й семестр`]), "Все семестры");
}

function groupQuery() {
  const query = new URLSearchParams();
  [["faculty_id", facultySelect], ["study_program_id", programSelect],
    ["academic_year", yearSelect], ["semester", semesterSelect]].forEach(([key, select]) => {
    if (select.value) query.set(key, select.value);
  });
  return query.toString();
}

async function loadGroups() {
  const requestId = ++groupsRequest;
  loadedGroups = [];
  updateRecommendationControls();
  groupsBody.replaceChildren();
  groupsBody.setAttribute("aria-busy", "true");
  groupsStatus.textContent = "Загрузка групп…";
  groupsStatus.dataset.error = "false";
  retryButton.hidden = true;
  try {
    const groups = await apiGetAll(`/groups/testing-overview?${groupQuery()}`);
    if (requestId !== groupsRequest) return;
    loadedGroups = groups;
    renderTestingMatrix(groups);
    updateRecommendationControls();
    groupsStatus.textContent = groups.length ? `Найдено групп: ${groups.length}` : "Группы по выбранным фильтрам не найдены.";
  } catch (error) {
    if (requestId !== groupsRequest) return;
    groupsStatus.textContent = `Не удалось загрузить группы: ${error.message}`;
    groupsStatus.dataset.error = "true";
    retryButton.hidden = false;
  } finally {
    if (requestId === groupsRequest) groupsBody.setAttribute("aria-busy", "false");
  }
}

async function loadReferences() {
  try {
    retryButton.hidden = true;
    groupsStatus.dataset.error = "false";
    groupsStatus.textContent = "Загрузка справочников…";
    const [departments, loadedPrograms, loadedPeriods, loadedDisciplines, actor] = await Promise.all([
      apiGetAll("/departments"), apiGetAll("/programs"), apiGetAll("/periods"), apiGetAll("/disciplines"),
      apiGet("/users/me").catch(() => null),
    ]);
    programs = loadedPrograms;
    periods = loadedPeriods;
    disciplines = loadedDisciplines;
    setDisciplineOptions();
    canManageRecommendations = Boolean(actor?.is_active && ["ADMIN", "LPR"].includes(actor.role));
    document.getElementById("recommendation-access").textContent = canManageRecommendations
      ? `${actor.full_name}. Отметьте группы в нужных периодах и сохраните изменения. Закрытые периоды доступны только для просмотра.`
      : "Просмотр списка. Изменять рекомендации могут ЛПР и администратор после входа в систему.";
    const faculties = departments.filter(department => ["FACULTY", "INSTITUTE"].includes(department.type));
    setOptions(facultySelect, faculties.map(faculty => [faculty.id, faculty.name]), "Все факультеты");
    setOptions(yearSelect, [...new Set(periods.map(period => period.academic_year))]
      .sort().reverse().map(year => [year, year]), "Все годы");
    updatePrograms();
    updateSemesters();
    referencesReady = true;
    updateListPeriod();
    [facultySelect, programSelect, yearSelect, semesterSelect].forEach(select => { select.disabled = false; });
    await loadGroups();
  } catch (error) {
    groupsStatus.textContent = `Не удалось загрузить справочники: ${error.message}`;
    groupsStatus.dataset.error = "true";
    retryButton.hidden = false;
  }
}

document.getElementById("group-filters").addEventListener("submit", event => event.preventDefault());
facultySelect.addEventListener("change", () => { updatePrograms(); loadGroups(); });
yearSelect.addEventListener("change", () => { updateSemesters(); updateListPeriod(); loadGroups(); });
programSelect.addEventListener("change", loadGroups);
semesterSelect.addEventListener("change", () => { updateListPeriod(); loadGroups(); });
retryButton.addEventListener("click", () => referencesReady ? loadGroups() : loadReferences());
loadReferences();


function semesterLabel(period) {
  return `${period.semester === 1 ? "Осень" : "Весна"} ${period.academic_year.split("/")[period.semester === 1 ? 0 : 1]}`;
}

function periodBuckets() {
  const today = new Date();
  const startYear = today.getMonth() >= 8 ? today.getFullYear() : today.getFullYear() - 1;
  const year = yearSelect.value || `${startYear}/${startYear + 1}`;
  const semester = semesterSelect.value || (yearSelect.value ? "" : (today.getMonth() >= 8 || today.getMonth() === 0 ? "1" : "2"));
  document.getElementById("period-context").textContent =
    `Относительно ${year} учебного года${semester ? `, ${semester}-го семестра` : ""}. Отметки показывают назначения, а не результаты студентов.`;
  const buckets = [[], [], []];
  periods.slice().sort((a, b) => a.academic_year.localeCompare(b.academic_year) || a.semester - b.semester || a.id - b.id).forEach(period => {
    const difference = period.academic_year.localeCompare(year) || (semester ? period.semester - Number(semester) : 0);
    buckets[difference < 0 ? 0 : difference > 0 ? 2 : 1].push(period);
  });
  return { buckets, year };
}

function testingMark(testings, future) {
  const mark = document.createElement("span");
  const statusLabels = { COMPLETED: "Проведено", IN_PROGRESS: "Проводится", PLANNED: "Запланировано", CANCELLED: "Отменено" };
  let state = "missing";
  let label = "Нет назначенного тестирования";
  let symbol = future ? "" : "×";
  if (testings.length) {
    if (testings.every(test => test.status === "CANCELLED")) state = "missing";
    else if (testings.some(test => test.status === "IN_PROGRESS")) state = "active";
    else if (testings.every(test => test.status === "COMPLETED" || test.status === "CANCELLED")) state = "completed";
    else state = "planned";
    symbol = state === "active" ? "◐" : state === "missing" ? "×" : "✓";
    label = testings.map(test => `${test.discipline_name}: ${statusLabels[test.status] || "Статус не указан"}${test.scheduled_at ? ` (${new Date(test.scheduled_at).toLocaleString("ru-RU")})` : " — дата не назначена"}`).join("; ");
  } else if (future) state = "empty";
  mark.className = `testing-mark testing-mark--${state}`;
  mark.textContent = symbol;
  mark.title = label;
  mark.setAttribute("role", "img");
  mark.setAttribute("aria-label", label);
  mark.tabIndex = 0;
  return mark;
}

function renderTestingMatrix(groups) {
  groupsBody.replaceChildren();
  const { buckets, year } = periodBuckets();
  const head = document.getElementById("groups-head");
  head.replaceChildren();
  const heading = document.createElement("tr");
  ["Группа", "Курс", "Предыдущие тестирования", "Текущие тестирования", "Планируемые тестирования"].forEach(text => {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = text;
    heading.append(cell);
  });
  head.append(heading);
  const programNames = new Map(programs.map(program => [program.id, program.name]));
  groups.forEach(group => {
    const row = document.createElement("tr");
    const groupCell = document.createElement("th");
    groupCell.scope = "row";
    groupCell.textContent = group.name;
    groupCell.title = programNames.get(group.study_program_id) || "Направление не указано";
    const history = document.createElement("button");
    history.type = "button";
    history.className = "button history-button";
    history.textContent = "История";
    history.setAttribute("aria-label", `История рекомендаций группы ${group.name}`);
    history.addEventListener("click", () => openRecommendationHistory(group));
    groupCell.append(document.createElement("br"), history);
    row.append(groupCell);
    const courseCell = document.createElement("td");
    const course = group.admission_year ? Number(year.split("/")[0]) - group.admission_year + 1 : null;
    courseCell.textContent = course && course > 0 ? String(course) : "—";
    row.append(courseCell);
    buckets.forEach((bucket, index) => {
      const cell = document.createElement("td");
      const content = document.createElement("div");
      content.className = "period-marks";
      if (!bucket.length) content.textContent = "—";
      bucket.forEach(period => {
        const item = document.createElement("div");
        item.className = "period-mark";
        const label = document.createElement("span");
        label.textContent = semesterLabel(period);
        label.title = period.name || label.textContent;
        item.append(label, testingMark((group.testings || []).filter(test => test.period_id === period.id), index === 2));
        item.append(recommendationChoice(group, period));
        content.append(item);
      });
      cell.append(content);
      row.append(cell);
    });
    groupsBody.append(row);
  });
}

function canEditPeriod(period) {
  const today = new Date();
  const localDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return period.status !== "CLOSED" && period.end_date >= localDate;
}

function updateListPeriod() {
  const available = periods.filter(period => (!yearSelect.value || period.academic_year === yearSelect.value) &&
    (!semesterSelect.value || String(period.semester) === semesterSelect.value));
  setOptions(listPeriodSelect, available.map(period => [period.id, `${period.name} (${period.academic_year})`]), "Выберите период");
  if (!listPeriodSelect.value && available.length === 1) listPeriodSelect.value = String(available[0].id);
  updateRecommendationControls();
}

function updateRecommendationControls() {
  const period = periods.find(item => String(item.id) === listPeriodSelect.value);
  const isSaving = savingRecommendations || savingDisciplines;
  const canSelect = canManageRecommendations && period && canEditPeriod(period) && loadedGroups.length && !isSaving;
  const hasSavedRecommendations = Boolean(period && loadedGroups.some(group =>
    (group.recommendations || []).some(record => record.period_id === period.id && record.recommended)));
  document.getElementById("select-visible").disabled = !canSelect;
  document.getElementById("clear-visible").disabled = !canSelect;
  document.getElementById("save-recommendations").disabled = !canManageRecommendations || !pendingRecommendations.size || isSaving;
  document.getElementById("discard-recommendations").disabled = !pendingRecommendations.size || isSaving;
  document.getElementById("export-recommendations").disabled = !period || pendingRecommendations.size > 0 || isSaving;
  document.getElementById("save-disciplines").disabled = !canManageRecommendations || !period || !canEditPeriod(period)
    || !hasSavedRecommendations || !selectedDisciplineIds().length || pendingRecommendations.size > 0 || isSaving;
  document.getElementById("recommendation-changes").textContent = pendingRecommendations.size
    ? `Несохранённых изменений: ${pendingRecommendations.size}` : "Нет несохранённых изменений";
  [facultySelect, programSelect, yearSelect, semesterSelect, listPeriodSelect, disciplineSelect].forEach(select => {
    select.disabled = !referencesReady || isSaving;
  });
}

function selectedDisciplineIds() {
  return Array.from(disciplineSelect.selectedOptions || []).map(option => Number(option.value)).filter(Boolean);
}

function recommendedGroups(period) {
  return loadedGroups.filter(group => (group.recommendations || []).some(record =>
    record.period_id === period.id && record.recommended));
}

function changeRecommendation(group, period, recommended) {
  const key = `${group.id}:${period.id}`;
  const original = (group.recommendations || []).find(record => record.period_id === period.id);
  if (recommended === Boolean(original?.recommended)) pendingRecommendations.delete(key);
  else pendingRecommendations.set(key, {
    group_id: group.id, period_id: period.id, recommended,
    expected_version: pendingRecommendations.get(key)?.expected_version ?? original?.version ?? 0,
  });
  recommendationStatus.textContent = "";
  updateRecommendationControls();
}

function recommendationChoice(group, period) {
  const label = document.createElement("label");
  label.className = "recommendation-choice";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  const record = (group.recommendations || []).find(item => item.period_id === period.id);
  const pending = pendingRecommendations.get(`${group.id}:${period.id}`);
  checkbox.checked = pending ? pending.recommended : Boolean(record?.recommended);
  checkbox.dataset.dirty = String(Boolean(pending));
  const enrolled = (group.enrolled_period_ids || []).includes(period.id);
  checkbox.disabled = !canManageRecommendations || !canEditPeriod(period) || !enrolled || savingRecommendations;
  checkbox.setAttribute("aria-label", `Рекомендовать группу ${group.name}: ${period.name}`);
  label.title = !enrolled ? "Группа не участвует в этом периоде" : !canEditPeriod(period)
    ? "Период закрыт для изменений" : record ? `Последнее изменение: ${record.changed_by_name}` : "Выбор группы для проверки остаточных знаний";
  const text = document.createElement("span");
  text.textContent = checkbox.checked ? "Рекомендована" : "Рекомендовать";
  checkbox.addEventListener("change", () => {
    changeRecommendation(group, period, checkbox.checked);
    checkbox.dataset.dirty = String(pendingRecommendations.has(`${group.id}:${period.id}`));
    text.textContent = checkbox.checked ? "Рекомендована" : "Рекомендовать";
  });
  label.append(checkbox, text);
  return label;
}

function selectVisibleRecommendations(recommended) {
  const period = periods.find(item => String(item.id) === listPeriodSelect.value);
  if (!period || !canManageRecommendations || !canEditPeriod(period) || savingRecommendations) return;
  loadedGroups.filter(group => (group.enrolled_period_ids || []).includes(period.id)).forEach(group => {
    changeRecommendation(group, period, recommended);
  });
  renderTestingMatrix(loadedGroups);
}

async function saveRecommendations() {
  if (!pendingRecommendations.size || savingRecommendations || !canManageRecommendations) return;
  if (pendingRecommendations.size > 5000) {
    recommendationStatus.textContent = "За один раз можно сохранить не больше 5000 изменений. Сузьте выбор групп.";
    recommendationStatus.dataset.error = "true";
    return;
  }
  savingRecommendations = true;
  updateRecommendationControls();
  renderTestingMatrix(loadedGroups);
  recommendationStatus.textContent = "Сохранение рекомендаций…";
  recommendationStatus.dataset.error = "false";
  try {
    await request("PUT", "/recommendations", { changes: [...pendingRecommendations.values()] });
    pendingRecommendations.clear();
    recommendationStatus.textContent = "Рекомендации сохранены.";
    await loadGroups();
  } catch (error) {
    recommendationStatus.textContent = `Изменения не сохранены: ${error.message}. Чтобы загрузить актуальные данные, нажмите «Отменить изменения».`;
    recommendationStatus.dataset.error = "true";
  } finally {
    savingRecommendations = false;
    updateRecommendationControls();
    renderTestingMatrix(loadedGroups);
  }
}

// Создаются только отсутствующие пары группа-дисциплина, чтобы не дублировать тестирования.
async function saveDisciplines() {
  const period = periods.find(item => String(item.id) === listPeriodSelect.value);
  const disciplineIds = selectedDisciplineIds();
  const groups = period ? recommendedGroups(period) : [];
  if (!period || !disciplineIds.length || !groups.length || pendingRecommendations.size || savingDisciplines) return;
  savingDisciplines = true;
  updateRecommendationControls();
  recommendationStatus.textContent = "Закрепление дисциплин…";
  recommendationStatus.dataset.error = "false";
  try {
    const existing = await apiGetAll(`/testing?period_id=${encodeURIComponent(period.id)}`);
    const existingPairs = new Set(existing.map(testing => `${testing.group_id}:${testing.discipline_id}`));
    const changes = groups.flatMap(group => disciplineIds.map(disciplineId => ({
      period_id: period.id, group_id: group.id, discipline_id: disciplineId,
    }))).filter(change => !existingPairs.has(`${change.group_id}:${change.discipline_id}`));
    if (!changes.length) {
      recommendationStatus.textContent = "Выбранные дисциплины уже закреплены за рекомендованными группами.";
      return;
    }
    if (changes.length > 5000) {
      recommendationStatus.textContent = "За один раз можно закрепить не больше 5000 дисциплин. Сузьте выбор.";
      recommendationStatus.dataset.error = "true";
      return;
    }
    let saved = 0;
    let failed = 0;
    for (const change of changes) {
      try {
        await apiPost("/testing", { ...change, status: "PLANNED" });
        saved += 1;
      } catch (_) {
        failed += 1;
      }
    }
    if (failed) {
      recommendationStatus.textContent = `Закреплено дисциплин: ${saved}; не сохранено: ${failed}. Повторите попытку для оставшихся пар.`;
      recommendationStatus.dataset.error = "true";
    } else {
      recommendationStatus.textContent = `Закреплено дисциплин: ${saved}.`;
    }
    await loadGroups();
  } catch (error) {
    recommendationStatus.textContent = `Не удалось закрепить дисциплины: ${error.message}`;
    recommendationStatus.dataset.error = "true";
  } finally {
    savingDisciplines = false;
    updateRecommendationControls();
  }
}

async function exportRecommendations() {
  if (!listPeriodSelect.value || pendingRecommendations.size) return;
  const button = document.getElementById("export-recommendations");
  button.disabled = true;
  const query = new URLSearchParams({ period_id: listPeriodSelect.value });
  if (facultySelect.value) query.set("faculty_id", facultySelect.value);
  if (programSelect.value) query.set("study_program_id", programSelect.value);
  try {
    const response = await fetch(`${API_BASE}/recommendations/export?${query}`);
    if (!response.ok) throw new Error((await response.json()).detail || "Не удалось сформировать список");
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `recommended-groups-${listPeriodSelect.value}.csv`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    recommendationStatus.textContent = "Список сформирован по сохранённым рекомендациям с учётом факультета и направления.";
    recommendationStatus.dataset.error = "false";
  } catch (error) {
    recommendationStatus.textContent = `Не удалось сформировать список: ${error.message}`;
    recommendationStatus.dataset.error = "true";
  } finally {
    updateRecommendationControls();
  }
}

let historyRequest = 0;
let historyGroup = null;
async function openRecommendationHistory(group) {
  historyGroup = group;
  const requestId = ++historyRequest;
  const dialog = document.getElementById("recommendation-history");
  const body = document.getElementById("history-body");
  const status = document.getElementById("history-status");
  const retry = document.getElementById("retry-history");
  document.getElementById("history-title").textContent = `История рекомендаций: ${group.name}`;
  body.replaceChildren();
  status.textContent = "Загрузка истории…";
  retry.hidden = true;
  if (!dialog.open) dialog.showModal();
  try {
    const history = await apiGetAll(`/recommendations/history?group_id=${group.id}`);
    if (requestId !== historyRequest) return;
    history.forEach(event => {
      const row = document.createElement("tr");
      [event.period_name, event.recommended ? "Рекомендована" : "Рекомендация снята", event.changed_by_name,
        new Date(event.changed_at).toLocaleString("ru-RU")].forEach(value => {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      });
      body.append(row);
    });
    status.textContent = history.length ? `Изменений: ${history.length}` : "Рекомендации для этой группы ещё не изменялись.";
  } catch (error) {
    if (requestId !== historyRequest) return;
    status.textContent = `Не удалось загрузить историю: ${error.message}`;
    retry.hidden = false;
  }
}

listPeriodSelect.addEventListener("change", updateRecommendationControls);
disciplineSelect.addEventListener("change", updateRecommendationControls);
document.getElementById("select-visible").addEventListener("click", () => selectVisibleRecommendations(true));
document.getElementById("clear-visible").addEventListener("click", () => selectVisibleRecommendations(false));
document.getElementById("save-recommendations").addEventListener("click", saveRecommendations);
document.getElementById("save-disciplines").addEventListener("click", saveDisciplines);
document.getElementById("discard-recommendations").addEventListener("click", () => {
  if (savingRecommendations) return;
  pendingRecommendations.clear();
  recommendationStatus.textContent = "Несохранённые изменения отменены.";
  recommendationStatus.dataset.error = "false";
  updateRecommendationControls();
  loadGroups();
});
document.getElementById("export-recommendations").addEventListener("click", exportRecommendations);
document.getElementById("close-history").addEventListener("click", () => {
  historyRequest++;
  document.getElementById("recommendation-history").close();
});
document.getElementById("recommendation-history").addEventListener("cancel", () => { historyRequest++; });
document.getElementById("retry-history").addEventListener("click", () => openRecommendationHistory(historyGroup));
window.addEventListener("beforeunload", event => {
  if (pendingRecommendations.size) { event.preventDefault(); event.returnValue = ""; }
});
