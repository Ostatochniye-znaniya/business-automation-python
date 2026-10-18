const facultySelect = document.getElementById("faculty");
const programSelect = document.getElementById("program");
const yearSelect = document.getElementById("academic-year");
const semesterSelect = document.getElementById("semester");
const groupsBody = document.getElementById("groups-body");
const groupsStatus = document.getElementById("groups-status");
const retryButton = document.getElementById("retry");
let programs = [];
let periods = [];
let groupsRequest = 0;
let referencesReady = false;

function setOptions(select, entries, placeholder) {
  const previous = select.value;
  select.replaceChildren(new Option(placeholder, ""));
  entries.forEach(([value, label]) => select.add(new Option(label, String(value))));
  if (entries.some(([value]) => String(value) === previous)) select.value = previous;
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
  groupsBody.replaceChildren();
  groupsBody.setAttribute("aria-busy", "true");
  groupsStatus.textContent = "Загрузка групп…";
  groupsStatus.dataset.error = "false";
  retryButton.hidden = true;
  try {
    const groups = await apiGetAll(`/groups/testing-overview?${groupQuery()}`);
    if (requestId !== groupsRequest) return;
    renderTestingMatrix(groups);
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
    const [departments, loadedPrograms, loadedPeriods] = await Promise.all([
      apiGetAll("/departments"), apiGetAll("/programs"), apiGetAll("/periods"),
    ]);
    programs = loadedPrograms;
    periods = loadedPeriods;
    const faculties = departments.filter(department => ["FACULTY", "INSTITUTE"].includes(department.type));
    setOptions(facultySelect, faculties.map(faculty => [faculty.id, faculty.name]), "Все факультеты");
    setOptions(yearSelect, [...new Set(periods.map(period => period.academic_year))]
      .sort().reverse().map(year => [year, year]), "Все годы");
    updatePrograms();
    updateSemesters();
    referencesReady = true;
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
yearSelect.addEventListener("change", () => { updateSemesters(); loadGroups(); });
programSelect.addEventListener("change", loadGroups);
semesterSelect.addEventListener("change", loadGroups);
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
        content.append(item);
      });
      cell.append(content);
      row.append(cell);
    });
    groupsBody.append(row);
  });
}
