const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../..');

class Element {
  constructor() {
    this.children = [];
    this.dataset = {};
    this.listeners = {};
    this.value = '';
    this.textContent = '';
    this.hidden = false;
    this.disabled = false;
    this.classes = new Set();
    this.classList = {
      add: (...names) => names.forEach(name => this.classes.add(name)),
      toggle: (name, force) => (force ?? !this.classes.has(name)) ? this.classes.add(name) : this.classes.delete(name),
      contains: name => this.classes.has(name),
    };
  }
  append(...children) { this.children.push(...children); }
  add(child) { this.append(child); }
  replaceChildren(...children) { this.children = children; this.value = ''; }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  setAttribute(name, value) { this[name] = value; }
  get className() { return [...this.classes].join(' '); }
  set className(value) { this.classes = new Set(String(value || '').split(/\s+/).filter(Boolean)); }
}
function environment(responder) {
  const elements = new Map();
  const document = {
    body: { dataset: { page: 'reports' } },
    getElementById(id) { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); },
    createElement: () => new Element(),
  };
  const context = { document, apiGetAll: responder || (async () => []), apiGet: async () => ({}), Option: class {
    constructor(text, value) { this.textContent = text; this.value = value; }
  } };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(root, 'frontend/js/pages/reports.js'), 'utf8'), context);
  return { context, get: id => document.getElementById(id) };
}
const settle = async () => { for (let index = 0; index < 5; index += 1) await new Promise(setImmediate); };

// Строка отчётов содержит пять ячеек, раскрывающаяся строка — одну.
const mainRows = env => env.get('reports-rows').children
  .filter(row => row.children.length === 5)
  .map(row => row.children.slice(0, 4).map(cell => cell.textContent));

const api = reportsParam => async url => {
  if (url === '/periods') return [{ id: 1, name: 'Весна', academic_year: '2024/2025', semester: 2 }];
  if (url === '/groups') return [{ id: 7, name: '223-111' }];
  if (url === '/disciplines') return [{ id: 9, name: 'Сети и телекоммуникации' }];
  if (url.startsWith('/testing?')) return [{ id: 12, group_id: 7, discipline_id: 9 }];
  if (url.startsWith('/reports?')) return reportsParam;
  assert.fail(url);
};

test('reports render group, discipline names and comments in details', async () => {
  const env = environment(api([
    { id: 21, knowledge_test_id: 12, electronic_status: 'Принят', paper_status: 'Получен',
      final_status: 'Принят', electronic_comment: 'Демонстрационный отчёт' },
  ]));
  await settle();
  env.get('testing').value = '12';
  await env.get('testing').listeners.change();
  await settle();
  assert.deepEqual(mainRows(env), [['223-111', 'Сети и телекоммуникации', 'Принят', 'Получен']]);
  assert.match(env.get('reports-status').textContent, /Найдено отчётов: 1/);
  assert.match(env.get('statistics-electronic').textContent, /1 из 1/);
  assert.equal(env.get('reports-pagination').hidden, true);
});

test('details toggle expands comments, actions update status locally', async () => {
  const env = environment(api([
    { id: 21, knowledge_test_id: 12, electronic_status: 'На проверке', paper_status: 'Получен',
      electronic_comment: 'Демо: ожидается проверка' },
  ]));
  await settle();
  env.get('testing').value = '12';
  await env.get('testing').listeners.change();
  await settle();
  const rowsBody = env.get('reports-rows');
  const detailsPanel = rowsBody.children[1].children[0].children[0];
  const comment = detailsPanel.children[0].children[0].children[1].textContent;
  const actions = detailsPanel.children[1];
  assert.equal(actions.children[0].classes.has('button--accept'), true);
  assert.equal(actions.children[1].classes.has('button--return'), true);
  actions.children[1].listeners.click();
  assert.equal(mainRows(env)[0][2], 'На доработке');
  assert.equal(comment, 'Демо: ожидается проверка');
});

test('filters narrow rows and status message reflects counts', async () => {
  const env = environment(api([
    { id: 1, knowledge_test_id: 12, electronic_status: 'Принят', paper_status: 'Не сдан' },
    { id: 2, knowledge_test_id: 12, electronic_status: 'Не сдан', paper_status: 'Получен' },
  ]));
  await settle();
  env.get('testing').value = '12';
  await env.get('testing').listeners.change();
  await settle();
  assert.equal(mainRows(env).length, 2);
  env.get('electronic-filter').value = 'Не сдан';
  env.get('electronic-filter').listeners.change();
  assert.deepEqual(mainRows(env), [
    ['223-111', 'Сети и телекоммуникации', 'Не сдан', 'Получен'],
  ]);
  assert.match(env.get('reports-status').textContent, /Найдено отчётов: 1/);
  env.get('electronic-filter').value = 'Не выбрано';
  env.get('paper-filter').value = 'Требует проверки';
  env.get('paper-filter').listeners.change();
  assert.equal(mainRows(env).length, 0);
  assert.match(env.get('reports-status').textContent, /Отчётов с выбранными статусами нет/);
});

test('summary search narrows list and creating starts numbering from 101', async () => {
  const env = environment();
  assert.equal(env.get('summary-list').children.length, 13);
  env.get('create-summary').listeners.click();
  assert.equal(env.get('summary-list').children.length, 14);
  env.get('summary-search').value = '№101';
  env.get('summary-search').listeners.input();
  assert.equal(env.get('summary-list').children.length, 1);
  assert.match(env.get('summary-list').children[0].textContent, /Сводный отчет №101 по результатам Проверки от /);
});

test('tabs switch panels and mark active tab', () => {
  const env = environment();
  assert.equal(env.get('check-panel').hidden, false);
  assert.equal(env.get('summary-panel').hidden, true);
  assert.equal(env.get('summary-tab').classes.has('is-active'), false);
  env.get('summary-tab').listeners.click();
  assert.equal(env.get('check-panel').hidden, true);
  assert.equal(env.get('summary-panel').hidden, false);
  assert.equal(env.get('summary-tab').classes.has('is-active'), true);
});

test('clearing period empties table and disables testing select', async () => {
  const env = environment(api([
    { id: 21, knowledge_test_id: 12, electronic_status: 'Принят', paper_status: 'Получен' },
  ]));
  await settle();
  env.get('testing').value = '12';
  await env.get('testing').listeners.change();
  await settle();
  assert.equal(mainRows(env).length, 1);
  env.get('period').value = '';
  await env.get('period').listeners.change();
  await settle();
  assert.equal(mainRows(env).length, 0);
  assert.equal(env.get('testing').disabled, true);
  assert.match(env.get('reports-status').textContent, /Выберите период тестирования/);
});
