(function () {
  const seedOrders = [
    { id: 1, title: 'Приказ “О проведении анкетирования и проверки остаточных знаний обучающихся” №000 от 12.12.12', year: '2025', semester: 'Весна', date: '12.12.12', draft: false },
    { id: 2, title: 'Приказ “О проведении анкетирования и проверки остаточных знаний обучающихся” №000 от 12.12.12', year: '2025', semester: 'Весна', date: '12.12.12', draft: false },
    { id: 3, title: 'Приказ “О проведении анкетирования и проверки остаточных знаний обучающихся” №000 от 12.12.12', year: '2025', semester: 'Весна', date: '12.12.12', draft: false },
    { id: 4, title: 'Приказ “О проведении анкетирования и проверки остаточных знаний обучающихся” №000 от 12.12.12', year: '2025', semester: 'Весна', date: '12.12.12', draft: false },
    { id: 5, title: 'Черновик “О проведении анкетирования и проверки остаточных знаний обучающихся” №000 от 12.12.12', year: '2025', semester: 'Весна', date: '12.12.12', draft: true },
    { id: 6, title: 'Черновик “О проведении анкетирования и проверки остаточных знаний обучающихся” №000 от 12.12.12', year: '2025', semester: 'Весна', date: '12.12.12', draft: true }
  ];
  const defaults = {
    bossControl: 'Иванов Иван Иванович', bossMethod: 'Иванов Иван Иванович',
    checkSummaryDate: '2024-07-19', surveySummaryDate: '2024-06-30', reportsDate: '2024-06-28',
    surveyMode: 'exact', surveyDate: '2024-06-04', surveyStart: '2024-06-04', surveyEnd: '2024-06-04'
  };
  let orders = (window.APP_CONFIG?.demoData ? seedOrders : []).map((order) => ({ ...defaults, ...order }));
  let nextId = orders.length + 1;
  let activeOrderId = null;

  const $ = (id) => document.getElementById(id);
  const search = $('orders-search');
  const tableBody = $('orders-table-body');
  const tableWrap = $('orders-table-wrap');
  const empty = $('orders-empty');
  const dialog = $('order-dialog');
  const createDialog = $('create-dialog');
  if (!search || !tableBody || !dialog || !createDialog) return;

  // Приказы и черновики используют общую последовательную нумерацию.
  function displayNumber(order) {
    return orders.indexOf(order) + 1;
  }
  function visibleOrders() {
    const query = search.value.trim().toLocaleLowerCase('ru');
    return orders.filter((order) => order.title.toLocaleLowerCase('ru').includes(query));
  }
  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  }
  function row(label, value, isPerson) {
    return '<div class="order-detail-row' + (isPerson ? ' order-detail-row--person' : '') + '"><span class="order-detail-label">' + escapeHtml(label) + '</span><span class="order-detail-value">' + escapeHtml(value) + '</span></div>';
  }
  function dateInput(name, label, value) {
    return '<label class="draft-field"><span>' + escapeHtml(label) + '</span><input type="date" name="' + name + '" value="' + escapeHtml(value) + '"></label>';
  }
  function textInput(name, label, value) {
    return '<label class="draft-field"><span>' + escapeHtml(label) + '</span><input type="text" name="' + name + '" value="' + escapeHtml(value) + '"></label>';
  }
  function surveyMarkup(order, editable) {
    if (!editable) {
      const survey = order.surveyMode === 'range'
        ? (order.surveyStart || '') + ' — ' + (order.surveyEnd || '')
        : (order.surveyDate || '');
      return row('Анкетирование:', survey, false);
    }
    return '<fieldset class="survey-time-field"><legend>Время анкетирования</legend>' +
      '<label class="survey-choice"><input type="radio" name="surveyMode" value="exact" ' + (order.surveyMode !== 'range' ? 'checked' : '') + '> Точное время</label>' +
      '<div class="survey-date-fields" data-survey-fields="exact"><label class="draft-field"><span>День анкетирования</span><input type="date" name="surveyDate" value="' + escapeHtml(order.surveyDate) + '"></label></div>' +
      '<label class="survey-choice"><input type="radio" name="surveyMode" value="range" ' + (order.surveyMode === 'range' ? 'checked' : '') + '> Диапазон дат</label>' +
      '<div class="survey-date-fields" data-survey-fields="range"><label class="draft-field"><span>День начала</span><input type="date" name="surveyStart" value="' + escapeHtml(order.surveyStart) + '"></label><label class="draft-field"><span>День окончания</span><input type="date" name="surveyEnd" value="' + escapeHtml(order.surveyEnd) + '"></label></div>' +
      '</fieldset>';
  }
  function renderDraftEditor(order, body) {
    body.innerHTML = '<form id="edit-draft-form" class="draft-edit-form">' +
      textInput('title', 'Название приказа', order.title.replace(/^Черновик\s*[“"]?/, '').replace(/[”"]$/, '')) +
      '<div class="draft-field-grid">' + textInput('year', 'Учебный год', order.year) +
      '<label class="draft-field"><span>Семестр</span><select name="semester"><option ' + (order.semester === 'Весна' ? 'selected' : '') + '>Весна</option><option ' + (order.semester === 'Осень' ? 'selected' : '') + '>Осень</option></select></label>' +
      dateInput('date', 'Дата приказа', toISODate(order.date)) + '</div>' +
      '<h3 class="draft-section-title">Ответственные сотрудники</h3>' + textInput('bossControl', 'Начальник отдела контроля образовательного процесса (ФИО)', order.bossControl) +
      textInput('bossMethod', 'Начальник центра по учебно-методической работе (ФИО)', order.bossMethod) +
      '<h3 class="draft-section-title">Сроки предоставления отчётов</h3><div class="draft-field-grid">' +
      dateInput('checkSummaryDate', 'Сводный отчёт по результатам проверки до', order.checkSummaryDate) +
      dateInput('surveySummaryDate', 'Сводный отчёт по результатам анкетирования до', order.surveySummaryDate) +
      dateInput('reportsDate', 'Отчёты по результатам проверки до', order.reportsDate) + '</div>' +
      surveyMarkup(order, true) +
      '<div class="dialog-actions"><button type="button" class="button button--secondary" id="cancel-draft-edit">Отмена</button><button type="submit" class="button button--primary">Сохранить изменения</button></div></form>';
    setupSurveyChoices(body);
    $('edit-draft-form').addEventListener('submit', saveDraftChanges);
    $('cancel-draft-edit').addEventListener('click', () => openOrder(order));
  }
  function openOrder(order) {
    activeOrderId = order.id;
    $('dialog-title').textContent = order.draft ? 'Черновики' : 'Приказы';
    $('dialog-number').textContent = (order.draft ? 'Черновик №' : 'Приказ №') + String(displayNumber(order)).padStart(3, '0');
    const body = $('dialog-body');
    const details = '<div class="order-details">' +
      row('Дата приказа:', displayDate(order.date), false) +
      row('Учебный год:', order.year, false) +
      row('Семестр:', order.semester, false) +
      row('Начальник отдела контроля образовательного процесса:', order.bossControl, true) +
      row('Начальник центра по учебно-методической работе:', order.bossMethod, true) +
      row('Сводный отчёт по результатам проверки до:', displayDate(order.checkSummaryDate), false) +
      row('Сводный отчёт по результатам анкетирования до:', displayDate(order.surveySummaryDate), false) +
      row('Отчёты по результатам проверки до:', displayDate(order.reportsDate), false) +
      surveyMarkup(order, false) + '</div>';
    if (order.draft) {
      body.innerHTML = '<div class="draft-view-actions"><button type="button" class="button button--primary" id="edit-draft-btn">Редактировать</button></div>' + details;
      $('edit-draft-btn').addEventListener('click', () => renderDraftEditor(order, body));
    } else {
      body.innerHTML = details;
    }
    if (!dialog.open) dialog.showModal();
  }
  function toISODate(value) {
    if (!value) return '';
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
    const parts = String(value).split('.');
    if (parts.length === 3) { const year = parts[2].length === 4 ? parts[2] : '20' + parts[2].padStart(2, '0'); return year + '-' + parts[1].padStart(2, '0') + '-' + parts[0].padStart(2, '0'); }
    return '';
  }
  function displayDate(value) {
    if (!value) return '—';
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      const [y, m, d] = value.split('-');
      return d + '.' + m + '.' + y;
    }
    return value;
  }
  function setupSurveyChoices(root) {
    const sync = () => {
      const selected = root.querySelector('input[name="surveyMode"]:checked')?.value || 'exact';
      root.querySelectorAll('[data-survey-fields]').forEach((block) => {
        const active = block.dataset.surveyFields === selected;
        block.hidden = !active;
        block.querySelectorAll('input').forEach((input) => { input.disabled = !active; });
      });
    };
    root.querySelectorAll('input[name="surveyMode"]').forEach((input) => input.addEventListener('change', sync));
    sync();
  }
  function saveDraftChanges(event) {
    event.preventDefault();
    const order = orders.find((item) => item.id === activeOrderId);
    if (!order || !order.draft) return;
    const data = new FormData(event.currentTarget);
    const rawTitle = String(data.get('title') || '').trim();
    if (!rawTitle) { event.currentTarget.elements.title.reportValidity(); return; }
    order.title = 'Черновик “' + rawTitle.replace(/^Черновик\s*[“"]?/, '').replace(/[”"]$/, '') + '”';
    ['year', 'semester', 'date', 'bossControl', 'bossMethod', 'checkSummaryDate', 'surveySummaryDate', 'reportsDate', 'surveyMode', 'surveyDate', 'surveyStart', 'surveyEnd'].forEach((key) => {
      if (data.has(key)) order[key] = String(data.get(key));
    });
    dialog.close();
    render();
  }
  function formOrderData(form) {
    const data = new FormData(form);
    const result = { ...defaults };
    ['title', 'year', 'semester', 'bossControl', 'bossMethod', 'checkSummaryDate', 'surveySummaryDate', 'reportsDate', 'surveyMode', 'surveyDate', 'surveyStart', 'surveyEnd'].forEach((key) => {
      if (data.has(key)) result[key] = String(data.get(key) || '');
    });
    result.date = String(data.get('date') || new Date().toISOString().slice(0, 10));
    return result;
  }
  function createRecord(draft) {
    const form = $('create-form');
    const values = formOrderData(form);
    const rawTitle = String(values.title || '').trim();
    if (!rawTitle) { form.elements.title.reportValidity(); return; }
    const cleanTitle = rawTitle.replace(/^Черновик\s*[“"]?/, '').replace(/[”"]$/, '');
    orders.push({ ...values, id: nextId++, title: (draft ? 'Черновик “' : 'Приказ “') + cleanTitle + '”', draft });
    search.value = '';
    form.reset();
    // Restore defaults after reset, including dates and survey mode.
    form.elements.year.value = '2025';
    form.elements.semester.value = 'Весна';
    form.elements.date.value = new Date().toISOString().slice(0, 10);
    form.elements.bossControl.value = defaults.bossControl;
    form.elements.bossMethod.value = defaults.bossMethod;
    form.elements.checkSummaryDate.value = defaults.checkSummaryDate;
    form.elements.surveySummaryDate.value = defaults.surveySummaryDate;
    form.elements.reportsDate.value = defaults.reportsDate;
    form.elements.surveyDate.value = defaults.surveyDate;
    form.elements.surveyStart.value = defaults.surveyStart;
    form.elements.surveyEnd.value = defaults.surveyEnd;
    setupSurveyChoices(form);
    createDialog.close();
    render();
  }

  function render() {
    const items = visibleOrders();
    tableBody.innerHTML = items.map((order) => '<tr data-id="' + order.id + '"><td>' + String(displayNumber(order)).padStart(3, '0') + '</td><td><span class="order-link">' + escapeHtml(order.title) + '</span></td><td>' + escapeHtml(order.year) + '</td><td>' + escapeHtml(order.semester) + '</td></tr>').join('');
    tableWrap.hidden = false;
    tableWrap.style.display = '';
    empty.hidden = items.length > 0;
    $('page-title').textContent = 'Приказы';
  }
  function handleOrderClick(event) {
    const rowEl = event.target.closest('[data-id]');
    if (!rowEl) return;
    const order = orders.find((item) => item.id === Number(rowEl.dataset.id));
    if (order) openOrder(order);
  }
  search.addEventListener('input', render);
  tableBody.addEventListener('click', handleOrderClick);
  $('new-order-btn').addEventListener('click', () => {
    const form = $('create-form');
    if (!form.elements.date.value) form.elements.date.value = new Date().toISOString().slice(0, 10);
    setupSurveyChoices(form);
    createDialog.showModal();
  });
  $('create-form').addEventListener('submit', (event) => {
    event.preventDefault();
    createRecord(false);
  });
  $('save-draft-btn').addEventListener('click', () => createRecord(true));
  setupSurveyChoices($('create-form'));
  [dialog, createDialog].forEach((item) => item.addEventListener('click', (event) => { if (event.target === item) item.close(); }));
  document.querySelectorAll('[data-close-dialog]').forEach((button) => button.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    const targetDialog = document.getElementById(button.dataset.closeDialog);
    if (targetDialog?.open) targetDialog.close();
  }));
  render();
})();
