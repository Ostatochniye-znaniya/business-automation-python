const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');

class Element {
  constructor() { this.children = []; this.dataset = {}; this.listeners = {}; this.value = ''; this.textContent = ''; }
  append(...children) { this.children.push(...children); }
  add(child) { this.append(child); }
  replaceChildren(...children) { this.children = children; this.value = ''; }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  setAttribute(name, value) { this[name] = value; }
}
function environment(page, apiGetAll, apiGet = async () => ({})) {
  const elements = new Map();
  const dispatchedEvents = [];
  const document = {
    body: { dataset: { page } }, documentElement: { dataset: {} },
    getElementById(id) { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); },
    createElement: () => new Element(),
    dispatchEvent(event) { dispatchedEvents.push(event); },
  };
  const context = { document, apiGetAll, apiGet, Option: class {
    constructor(text, value) { this.textContent = text; this.value = value; }
  }, CustomEvent: class {
    constructor(type, options) { this.type = type; this.detail = options.detail; }
  }};
  vm.createContext(context);
  return { context, elements, dispatchedEvents, get: id => document.getElementById(id) };
}
const settle = () => new Promise(resolve => setImmediate(resolve));
function execute(env, file = 'pages/sections.js') {
  vm.runInContext(fs.readFileSync(path.join(root, 'frontend/js', file), 'utf8'), env.context);
}
const period = { id: 1, name: 'Весна', academic_year: '2025/2026', semester: 2,
  start_date: '2026-02-01', end_date: '2026-06-30', status: 'OPEN' };
const values = env => env.get('section-rows').children.map(row => row.children.map(cell => cell.textContent));

test('home shows unknown indicators without fabricating zero counts', async () => {
  const env = environment('home', async () => [period], async () => ({ departments: [
    { name: 'ФИТ', groups: {}, disciplines: {}, reports: {} },
  ] }));
  execute(env); await settle();
  assert.deepEqual(values(env), [['ФИТ', '— / —', '— / —', '—', '—']]);
});

test('slow earlier dashboard response cannot overwrite the latest selection', async () => {
  let finishOld;
  const env = environment('home', async () => [period], async url => {
    if (url.endsWith('=1')) return new Promise(resolve => { finishOld = resolve; });
    return { departments: [] };
  });
  execute(env); await settle();
  env.get('period').value = '2';
  await env.get('period').listeners.change();
  finishOld({ departments: [{ name: 'Old data', groups: {}, disciplines: {}, reports: {} }] });
  await settle();
  assert.equal(env.get('section-status').textContent, 'Подразделения не найдены.');
  assert.equal(values(env).length, 0);
});

test('access filters names and roles, rendering server values as text', async () => {
  const env = environment('access', async () => [
    { full_name: '<script>test</script>', email: 'teacher@test', role: 'TEACHER', is_active: true },
    { full_name: 'Другой', role: 'GUEST', is_active: false },
  ]);
  execute(env); await settle();
  env.get('user-search').value = 'TEACHER@';
  env.get('user-search').listeners.input();
  assert.equal(values(env)[0][0], '<script>test</script>');
  env.get('user-role').value = 'GUEST';
  env.get('user-role').listeners.change();
  assert.equal(values(env).length, 0);
});

test('reports fetch selected test reports and clear rows when period is cleared', async () => {
  const env = environment('reports', async url => {
    if (url === '/periods') return [period];
    if (url === '/groups') return [{ id: 3, name: '241-001' }];
    if (url === '/disciplines') return [{ id: 4, name: 'Базы данных' }];
    if (url.startsWith('/testing?')) return [{ id: 5, group_id: 3, discipline_id: 4 }];
    assert.equal(url, '/reports?knowledge_test_id=5');
    return [{ id: 6, electronic_status: 'Сдан', final_status: 'Принят' }];
  });
  execute(env); await settle();
  assert.equal(env.get('testing').disabled, false);
  env.get('testing').value = '5';
  await env.get('testing').listeners.change();
  assert.equal(values(env)[0][1], 'Сдан');
  env.get('period').value = '';
  await env.get('period').listeners.change();
  assert.equal(values(env).length, 0);
  assert.equal(env.get('testing').disabled, true);
});

test('failed request exposes retry and a successful retry clears the error', async () => {
  let fail = true;
  const env = environment('periods', async () => { if (fail) throw Error('Offline'); return [period]; });
  execute(env); await settle();
  assert.equal(env.get('section-status').dataset.error, 'true');
  assert.equal(env.get('section-retry').hidden, false);
  fail = false;
  await env.get('section-retry').listeners.click();
  assert.equal(env.get('section-status').dataset.error, 'false');
  assert.equal(env.get('semester-filter').value, '1');
});

test('period settings select semester and edit deadline dates in the matching sections', async () => {
  const autumn = { ...period, id: 2, name: 'Осень', academic_year: '2025/2026', semester: 1,
    start_date: '2025-09-01', end_date: '2025-12-31' };
  const env = environment('periods', async () => [period, autumn]);
  execute(env); await settle();
  assert.deepEqual(env.get('semester-filter').children.map(option => option.value), ['', '1', '2']);
  assert.equal(env.get('semester-filter').children[1].textContent, 'Весна 2026');
  assert.equal(env.get('semester-filter').value, '1');
  env.get('semester-filter').value = '1';
  env.get('semester-filter').listeners.change();
  assert.equal(env.get('schedule-deadlines').children.length, 3);
  assert.equal(env.get('report-deadlines').children.length, 3);
  const startDate = env.get('schedule-deadlines').children[0].children[1].children[0];
  assert.equal(startDate.value, '2025-01-01');
  startDate.value = '2026-02-02';
  startDate.listeners.change();
  assert.equal(env.dispatchedEvents[0].type, 'testing-period-deadline-changed');
  assert.deepEqual(JSON.parse(JSON.stringify(env.dispatchedEvents[0].detail)), {
    periodId: period.id,
    semester: period.semester,
    deadline: 'student-lists',
    dateType: 'start',
    date: '2026-02-02',
  });
  assert.match(env.get('section-status').textContent, /API сохранения сроков ещё не подключён/);
  env.get('semester-filter').value = '2';
  env.get('semester-filter').listeners.change();
  env.get('semester-filter').value = '1';
  env.get('semester-filter').listeners.change();
  assert.equal(env.get('schedule-deadlines').children[0].children[1].children[0].value, '2026-02-02');
});

test('theme bootstrap uses both old storage keys and survives unavailable storage', () => {
  const env = environment('settings');
  env.context.localStorage = { getItem: key => key === 'app-theme' ? 'dark' : null };
  execute(env, 'theme.js');
  assert.equal(env.context.document.documentElement.dataset.theme, 'dark');
  env.context.localStorage.getItem = () => { throw Error('Storage blocked'); };
  execute(env, 'theme.js');
  assert.equal(env.context.document.documentElement.dataset.theme, 'light');
});

test('sidebar links resolve and access navigation stays active on date settings', () => {
  const env = environment('settings');
  env.context.window = { location: { pathname: '/pages/optionsDate.html' } };
  env.context.localStorage = { setItem() {} };
  execute(env, 'layout.js');
  const sidebar = env.get('sidebar').innerHTML;
  assert.match(sidebar, /href="\/pages\/access.html" aria-current="page"/);
  assert.match(sidebar, /Проверка<br>остаточных знаний/);
  for (const [, href] of sidebar.matchAll(/href="([^"]+)"/g)) {
    assert.ok(fs.existsSync(path.join(root, 'frontend', href === '/' ? 'index.html' : href)));
  }
});
