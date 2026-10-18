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
    const groups = await apiGetAll(`/groups?${groupQuery()}`);
    if (requestId !== groupsRequest) return;
    const programNames = new Map(programs.map(program => [program.id, program.name]));
    groups.forEach(group => {
      const row = document.createElement("tr");
      [group.name, programNames.get(group.study_program_id) || "Не указано"].forEach(value => {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      });
      groupsBody.append(row);
    });
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
