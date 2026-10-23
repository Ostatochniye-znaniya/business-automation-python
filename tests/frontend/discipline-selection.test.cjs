const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
  constructor() {
    this.listeners = {};
    this.dataset = {};
    this.options = [
      { value: '', textContent: 'Не выбрано' },
      { value: '1', textContent: 'Линейная алгебра' },
      { value: '2', textContent: 'Базы данных' },
    ];
    this.value = '';
    this.hidden = false;
    this.open = false;
    this.textContent = '';
  }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  showModal() { this.open = true; }
  close() { this.open = false; }
  focus() {}
  get selectedIndex() { return this.options.findIndex(option => option.value === this.value); }
}

function setup() {
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  };
  const events = [];
  const context = {
    document: {
      getElementById: get,
      dispatchEvent: event => events.push(event),
    },
    CustomEvent: class {
      constructor(type, options) { this.type = type; this.detail = options.detail; }
    },
    Map,
    Number,
  };
  vm.createContext(context);
  vm.runInContext(
    fs.readFileSync(path.resolve(__dirname, '../../frontend/js/pages/discipline-selection.js'), 'utf8'),
    context,
  );
  return { get, events };
}

function clickGroup(env, id = '21', name = '221-111') {
  const trigger = { dataset: { groupId: id, groupName: name } };
  env.get('groups-body').listeners.click({ target: { closest: () => trigger } });
}

test('discipline modal validates, clears, confirms, and restores a group selection', () => {
  const env = setup();
  const first = env.get('discipline-selection-first');
  const second = env.get('discipline-selection-second');
  const dialog = env.get('discipline-selection-dialog');
  const error = env.get('discipline-selection-error');

  clickGroup(env);
  assert.equal(env.get('discipline-selection-title').textContent, 'Выбор дисциплин для группы 221-111');
  env.get('discipline-selection-confirm').listeners.click();
  assert.match(error.textContent, /Выберите две дисциплины/);

  first.value = '1';
  second.value = '2';
  env.get('discipline-selection-clear').listeners.click();
  assert.equal(first.value, '');
  assert.equal(second.value, '');

  first.value = '1';
  second.value = '2';
  env.get('discipline-selection-confirm').listeners.click();
  assert.equal(dialog.open, false);
  assert.deepEqual(JSON.parse(JSON.stringify(env.events[0].detail)), {
    groupId: 21,
    groupName: '221-111',
    disciplineIds: [1, 2],
    disciplineNames: ['Линейная алгебра', 'Базы данных'],
  });

  clickGroup(env);
  assert.equal(String(first.value), '1');
  assert.equal(String(second.value), '2');
  env.get('discipline-selection-back').listeners.click();
  assert.equal(dialog.open, false);
});
