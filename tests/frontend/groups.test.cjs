const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
  constructor() { this.children = []; this.dataset = {}; this.listeners = {}; this.value = ''; this.textContent = ''; this.attributes = {}; }
  append(...children) { this.children.push(...children); }
  add(child) { this.append(child); }
  replaceChildren(...children) { this.children = children; this.value = ''; }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(key, callback) { this.listeners[key] = callback; }
  showModal() { this.open = true; }
  close() { this.open = false; }
}
function setup({ role = 'LPR', failure = false } = {}) {
  const elements = new Map();
  const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const periods = [
    { id: 1, name: 'Открытый период', academic_year: '2026/2027', semester: 1, status: 'OPEN', end_date: '2999-01-01' },
    { id: 2, name: 'Закрытый период', academic_year: '2025/2026', semester: 2, status: 'CLOSED', end_date: '2000-01-01' },
  ];
  const groups = [1, 2].map(id => ({ id, name: `Группа ${id}`, study_program_id: 1,
    admission_year: 2025, testings: [], recommendations: [], enrolled_period_ids: id === 1 ? [1, 2] : [1] }));
  const calls = [];
  let fail = failure;
  const context = {
    document: { getElementById: get, createElement: () => new Element() },
    window: { addEventListener() {} }, Option: class { constructor(text, value) { this.textContent = text; this.value = value; } },
    URLSearchParams, Date, Map, Set, setTimeout,
    apiGet: async () => ({ id: 2, full_name: 'ЛПР', role, is_active: true }),
    apiGetAll: async url => {
      if (url === '/periods') return periods;
      if (url === '/departments') return [{ id: 1, name: 'Факультет', type: 'FACULTY' }];
      if (url === '/programs') return [{ id: 1, name: 'Направление', faculty_id: 1 }];
      if (url.startsWith('/recommendations/history?')) return [{ period_name: 'Открытый период', recommended: true,
        changed_by_name: 'ЛПР', changed_at: '2026-10-18T10:00:00Z' }];
      return structuredClone(groups);
    },
    request: async (method, url, body) => {
      calls.push({ method, url, body });
      if (fail) throw Error('Список изменён другим пользователем');
      for (const change of body.changes) {
        const group = groups.find(item => item.id === change.group_id);
        group.recommendations = [{ ...change, version: change.expected_version + 1, changed_by_name: 'ЛПР' }];
      }
      return [];
    },
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.resolve(__dirname, '../../frontend/js/pages/groups.js'), 'utf8'), context);
  return { get, context, calls, groups, setFailure: value => { fail = value; } };
}
const settle = () => new Promise(resolve => setImmediate(resolve));
const evaluate = (env, code) => vm.runInContext(code, env.context);
function descendants(element) { return element.children.flatMap(child => [child, ...descendants(child)]); }
function checkbox(env, label) {
  return descendants(env.get('groups-body')).find(element => element.type === 'checkbox' && element.attributes['aria-label'] === label);
}

test('recommendations are editable only for an eligible open period and authorized actor', async () => {
  const env = setup(); await settle();
  assert.equal(checkbox(env, 'Рекомендовать группу Группа 1: Открытый период').disabled, false);
  assert.equal(checkbox(env, 'Рекомендовать группу Группа 1: Закрытый период').disabled, true);
  assert.equal(checkbox(env, 'Рекомендовать группу Группа 2: Закрытый период').disabled, true);
  const guest = setup({ role: 'GUEST' }); await settle();
  assert.equal(checkbox(guest, 'Рекомендовать группу Группа 1: Открытый период').disabled, true);
});

test('save persists the selected pair with its expected version and clears pending state', async () => {
  const env = setup(); await settle();
  const input = checkbox(env, 'Рекомендовать группу Группа 1: Открытый период');
  input.checked = true; input.listeners.change();
  assert.equal(env.get('save-recommendations').disabled, false);
  await env.get('save-recommendations').listeners.click();
  assert.equal(env.calls.length, 1);
  const { method, url, body } = env.calls[0];
  assert.equal(method, 'PUT'); assert.equal(url, '/recommendations');
  assert.deepEqual(JSON.parse(JSON.stringify(body)), { changes: [{ group_id: 1, period_id: 1, recommended: true, expected_version: 0 }] });
  assert.equal(evaluate(env, 'pendingRecommendations.size'), 0);
  assert.equal(checkbox(env, 'Рекомендовать группу Группа 1: Открытый период').checked, true);
});

test('server conflict preserves user changes and cancelling reloads the saved state', async () => {
  const env = setup({ failure: true }); await settle();
  const input = checkbox(env, 'Рекомендовать группу Группа 1: Открытый период');
  input.checked = true; input.listeners.change();
  await env.get('save-recommendations').listeners.click();
  assert.equal(evaluate(env, 'pendingRecommendations.size'), 1);
  assert.match(env.get('recommendation-status').textContent, /Изменения не сохранены/);
  env.get('discard-recommendations').listeners.click(); await settle();
  assert.equal(evaluate(env, 'pendingRecommendations.size'), 0);
  assert.equal(checkbox(env, 'Рекомендовать группу Группа 1: Открытый период').checked, false);
});

test('pending selections survive filtering and bulk selection affects only visible enrolled groups', async () => {
  const env = setup(); await settle();
  env.get('list-period').value = '1';
  env.get('select-visible').listeners.click();
  assert.equal(evaluate(env, 'pendingRecommendations.size'), 2);
  await evaluate(env, 'loadGroups()');
  assert.equal(checkbox(env, 'Рекомендовать группу Группа 1: Открытый период').checked, true);
  assert.equal(env.get('export-recommendations').disabled, true);
  env.get('clear-visible').listeners.click();
  assert.equal(evaluate(env, 'pendingRecommendations.size'), 0);
});

test('group history opens and renders saved changes', async () => {
  const env = setup(); await settle();
  await evaluate(env, 'openRecommendationHistory(loadedGroups[0])');
  assert.equal(env.get('recommendation-history').open, true);
  assert.equal(env.get('history-body').children.length, 1);
  assert.equal(env.get('history-body').children[0].children[2].textContent, 'ЛПР');
  env.get('close-history').listeners.click();
  assert.equal(env.get('recommendation-history').open, false);
});
