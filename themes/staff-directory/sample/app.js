/* Northstar People — staff directory sample.
   Vanilla JS, localStorage persistence, no external dependencies. */
(function () {
  'use strict';

  var KEY = 'stitchcraft:staff-directory:v1';
  var DEPARTMENTS = ['Engineering', 'Design', 'Product', 'Operations', 'People'];
  var STATUS_LABEL = { active: 'Active', new: 'New hire', 'on-leave': 'On leave' };
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (value) { return String(value == null ? '' : value); };
  var state = { employees: [], tasks: [], query: '', department: 'all', status: 'all', selected: null, editing: null };

  function uid(prefix) { return prefix + '-' + Math.random().toString(36).slice(2, 8); }
  function isoDaysAgo(days) {
    var date = new Date(); date.setDate(date.getDate() - days); return date.toISOString().slice(0, 10);
  }
  function initials(name) {
    return String(name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(function (part) { return part[0].toUpperCase(); }).join('');
  }
  function labelStatus(status) { return STATUS_LABEL[status] || status; }

  function seed() {
    var people = [
      ['Mara Chen', 'Staff Engineer', 'Engineering', 'Portland', 'active', 940],
      ['Ilya Novak', 'Design Lead', 'Design', 'Portland', 'active', 870],
      ['Avery Brooks', 'Product Manager', 'Product', 'Remote', 'active', 640],
      ['Priya Raman', 'People Partner', 'People', 'Portland', 'active', 510],
      ['Jon Bell', 'Operations Manager', 'Operations', 'Remote', 'active', 460],
      ['Sofia Reyes', 'Senior Engineer', 'Engineering', 'Remote', 'active', 320],
      ['Theo Laurent', 'Brand Designer', 'Design', 'Portland', 'new', 12],
      ['Nia Okafor', 'Product Analyst', 'Product', 'Remote', 'new', 8],
      ['Samir Haddad', 'Support Lead', 'Operations', 'Portland', 'active', 390],
      ['Elena Park', 'Frontend Engineer', 'Engineering', 'Remote', 'active', 250],
      ['Marcus Green', 'Recruiter', 'People', 'Portland', 'active', 210],
      ['Yuki Tan', 'UX Researcher', 'Design', 'Remote', 'on-leave', 180],
      ['Clara Moss', 'Finance Ops', 'Operations', 'Portland', 'active', 150],
      ['Owen Price', 'Product Designer', 'Design', 'Portland', 'active', 96],
      ['Leila Haddad', 'Data Engineer', 'Engineering', 'Remote', 'new', 5]
    ];
    state.employees = people.map(function (item, index) {
      var name = item[0];
      return {
        id: 'emp-' + (index + 1), name: name, role: item[1], department: item[2],
        location: item[3], status: item[4], started_on: isoDaysAgo(item[5]),
        email: name.toLowerCase().replace(/[^a-z ]/g, '').replace(/\s+/g, '.') + '@northstar.example'
      };
    });
    state.tasks = [
      ['emp-7', 'Sign the handbook', 'People', 4, true], ['emp-7', 'Meet the design team', 'Ilya Novak', 4, false],
      ['emp-7', 'Set up payroll', 'Finance Ops', 5, false], ['emp-8', 'Analytics access', 'Avery Brooks', 2, true],
      ['emp-8', 'Product onboarding', 'Avery Brooks', 6, false], ['emp-15', 'Laptop + accounts', 'Operations', 2, false],
      ['emp-15', 'Security training', 'People', 8, false], ['emp-15', 'Meet the platform team', 'Mara Chen', 5, false]
    ].map(function (item) {
      return { id: uid('task'), employee_id: item[0], task: item[1], owner: item[2], due_on: isoDaysAgo(-item[3]), done: item[4] };
    });
  }

  function load() {
    var saved = null;
    try { saved = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (error) { saved = null; }
    if (saved && Array.isArray(saved.employees) && Array.isArray(saved.tasks)) {
      state.employees = saved.employees; state.tasks = saved.tasks;
    } else { seed(); save(); }
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify({ employees: state.employees, tasks: state.tasks })); }
    catch (error) { toast('Local storage is unavailable — changes only last until reload.'); }
  }

  function toast(message) {
    var node = $('toast'); if (!node) return;
    node.textContent = message; node.hidden = false;
    clearTimeout(toast.timer); toast.timer = setTimeout(function () { node.hidden = true; }, 3200);
  }

  function employeeById(id) { return state.employees.find(function (person) { return person.id === id; }) || null; }
  function tasksFor(id) { return state.tasks.filter(function (task) { return task.employee_id === id; }); }
  function isVisible(person) {
    var haystack = [person.name, person.role, person.department, person.email, person.location].join(' ').toLowerCase();
    if (state.query && haystack.indexOf(state.query.toLowerCase()) < 0) return false;
    if (state.department !== 'all' && person.department !== state.department) return false;
    if (state.status !== 'all' && person.status !== state.status) return false;
    return true;
  }

  function renderStats() {
    var people = state.employees.length;
    var depts = new Set(state.employees.map(function (person) { return person.department; })).size;
    var newHires = state.employees.filter(function (person) { return person.status === 'new'; }).length;
    var open = state.tasks.filter(function (task) { return !task.done; }).length;
    $('stat-headcount').textContent = people;
    $('stat-departments').textContent = depts;
    $('stat-new').textContent = newHires;
    $('stat-tasks').textContent = open;
  }

  function renderChips() {
    var host = $('department-chips'); if (!host) return;
    host.textContent = '';
    [{ id: 'all', label: 'All' }].concat(DEPARTMENTS.map(function (name) { return { id: name, label: name }; })).forEach(function (item) {
      var button = document.createElement('button');
      button.type = 'button'; button.className = 'chip'; button.textContent = item.label;
      button.setAttribute('aria-pressed', String(state.department === item.id));
      button.addEventListener('click', function () { state.department = item.id; renderAll(); });
      host.appendChild(button);
    });
  }

  function renderDirectory() {
    var host = $('groups'); if (!host) return;
    host.textContent = '';
    var visible = state.employees.filter(isVisible);
    var byDepartment = {};
    visible.forEach(function (person) { (byDepartment[person.department] = byDepartment[person.department] || []).push(person); });
    var order = DEPARTMENTS.filter(function (name) { return byDepartment[name]; });
    var template = $('group-template');
    order.forEach(function (department) {
      if (!byDepartment[department]) return;
      var group = template.content.firstElementChild.cloneNode(true);
      group.querySelector('.group__name').textContent = department;
      group.querySelector('.group__count').textContent = byDepartment[department].length + ' people';
      var cards = group.querySelector('.cards');
      byDepartment[department].sort(function (a, b) { return a.name.localeCompare(b.name); }).forEach(function (person) {
        var card = $('card-template').content.firstElementChild.cloneNode(true);
        card.addEventListener('click', function () { openDrawer(person.id); });
        card.querySelector('.avatar').textContent = initials(person.name);
        card.querySelector('.person-card__name').textContent = person.name;
        var status = card.querySelector('.person-card__status');
        status.textContent = labelStatus(person.status); status.dataset.status = person.status;
        card.querySelector('.person-card__role').textContent = person.role;
        card.querySelector('.person-card__meta').textContent = person.department + ' · ' + person.location;
        cards.appendChild(card);
      });
      host.appendChild(group);
    });
    $('empty').hidden = visible.length > 0;
    $('result-line').textContent = visible.length
      ? visible.length + ' of ' + state.employees.length + ' people' + (state.query ? ' matching “' + state.query + '”' : '')
      : 'No matches';
    $('search-hint').textContent = visible.length === state.employees.length
      ? 'Type to filter the whole directory.' : visible.length + ' result' + (visible.length === 1 ? '' : 's') + ' shown.';
  }

  function renderProgress() {
    var done = state.tasks.filter(function (task) { return task.done; }).length;
    var total = state.tasks.length;
    var pct = total ? Math.round((done / total) * 100) : 0;
    $('progress-ring').style.setProperty('--pct', pct + '%');
    const value = $('progress-value'); if (value) value.textContent = pct + '%';
    $('progress-ring').setAttribute('aria-label', pct + '% of onboarding tasks complete');
    $('progress-copy').textContent = total ? done + ' of ' + total + ' onboarding tasks done across the team.' : 'No tasks yet.';
  }

  function renderAll() { renderStats(); renderChips(); renderDirectory(); renderProgress(); }

  function openDrawer(id) {
    var person = employeeById(id); if (!person) return;
    state.selected = id;
    $('drawer-avatar').textContent = initials(person.name);
    $('drawer-name').textContent = person.name;
    $('drawer-role').textContent = person.role;
    var status = $('drawer-status'); status.textContent = labelStatus(person.status); status.dataset.status = person.status;
    $('drawer-department').textContent = person.department;
    $('drawer-location').textContent = person.location || '—';
    $('drawer-started').textContent = formatDate(person.started_on);
    var email = $('drawer-email'); email.textContent = person.email; email.href = 'mailto:' + person.email;
    renderTasks(person);
    $('drawer').classList.add('is-open'); $('drawer').setAttribute('aria-hidden', 'false');
    $('scrim').hidden = false; $('drawer-close').focus();
  }

  function formatDate(value) {
    if (!value) return '—';
    var date = new Date(value + 'T12:00:00');
    return isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
  }

  function renderTasks(person) {
    var list = $('task-list'); list.textContent = '';
    var tasks = tasksFor(person.id);
    tasks.forEach(function (task) {
      var row = $('task-template').content.firstElementChild.cloneNode(true);
      var input = row.querySelector('input');
      input.checked = Boolean(task.done);
      input.setAttribute('aria-label', task.task);
      input.addEventListener('change', function () { task.done = input.checked; save(); renderProgress(); renderTasks(person); });
      row.querySelector('.task__text').textContent = task.task;
      row.querySelector('.task__due').textContent = task.done ? 'Done' : 'Due ' + formatDate(task.due_on);
      list.appendChild(row);
    });
    var done = tasks.filter(function (task) { return task.done; }).length;
    $('task-progress').textContent = done + ' / ' + tasks.length;
    $('task-progress-fill').style.width = (tasks.length ? Math.round((done / tasks.length) * 100) : 0) + '%';
    if (!tasks.length) {
      var empty = document.createElement('li'); empty.className = 'task'; empty.textContent = 'No onboarding tasks yet.'; list.appendChild(empty);
    }
  }

  function closeDrawer() {
    $('drawer').classList.remove('is-open'); $('drawer').setAttribute('aria-hidden', 'true');
    $('scrim').hidden = true; state.selected = null;
  }

  function openForm(person) {
    state.editing = person ? person.id : null;
    $('person-dialog-title').textContent = person ? 'Edit employee' : 'Add employee';
    $('field-name').value = person ? person.name : '';
    $('field-role').value = person ? person.role : '';
    $('field-department').value = person ? person.department : DEPARTMENTS[0];
    $('field-status').value = person ? person.status : 'active';
    $('field-email').value = person ? person.email : '';
    $('field-location').value = person ? person.location : 'Portland';
    $('field-started').value = person ? person.started_on : new Date().toISOString().slice(0, 10);
    $('form-error').hidden = true;
    var dialog = $('person-dialog');
    if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', '');
    $('field-name').focus();
  }
  function closeForm() { var dialog = $('person-dialog'); if (typeof dialog.close === 'function') dialog.close(); else dialog.removeAttribute('open'); }

  function submitForm(event) {
    event.preventDefault();
    var data = {
      name: $('field-name').value.trim(), role: $('field-role').value.trim(),
      department: $('field-department').value, status: $('field-status').value,
      email: $('field-email').value.trim(), location: $('field-location').value.trim(),
      started_on: $('field-started').value
    };
    if (!data.name || !data.role || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
      $('form-error').textContent = 'Add a name, role and a complete email address.';
      $('form-error').hidden = false; return;
    }
    if (state.editing) {
      var existing = employeeById(state.editing);
      if (existing) Object.keys(data).forEach(function (key) { existing[key] = data[key]; });
      toast(data.name + ' updated.');
      if (state.selected === state.editing) openDrawer(state.editing);
    } else {
      var person = Object.assign({ id: uid('emp') }, data);
      state.employees.push(person);
      state.tasks.push({ id: uid('task'), employee_id: person.id, task: 'Sign the handbook', owner: 'People', due_on: isoDaysAgo(-7), done: false });
      state.tasks.push({ id: uid('task'), employee_id: person.id, task: 'Meet the team', owner: person.department, due_on: isoDaysAgo(-10), done: false });
      toast(person.name + ' added to the directory.');
    }
    save(); closeForm(); renderAll();
  }

  function bind() {
    $('search').addEventListener('input', function (event) { state.query = event.target.value.trim(); renderDirectory(); });
    $('status-filter').addEventListener('change', function (event) { state.status = event.target.value; renderDirectory(); });
    $('clear-filters').addEventListener('click', function () {
      state.query = ''; state.department = 'all'; state.status = 'all';
      $('search').value = ''; $('status-filter').value = 'all'; renderAll(); $('search').focus();
    });
    $('add-person').addEventListener('click', function () { openForm(null); });
    $('drawer-close').addEventListener('click', closeDrawer);
    $('scrim').addEventListener('click', closeDrawer);
    $('drawer-edit').addEventListener('click', function () { var person = employeeById(state.selected); if (person) openForm(person); });
    $('dialog-close').addEventListener('click', closeForm);
    $('dialog-cancel').addEventListener('click', closeForm);
    $('person-form').addEventListener('submit', submitForm);
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') { closeDrawer(); closeForm(); }
      if (event.key === '/' && document.activeElement !== $('search')) { event.preventDefault(); $('search').focus(); }
    });
    var select = $('field-department');
    DEPARTMENTS.forEach(function (name) { var option = document.createElement('option'); option.value = name; option.textContent = name; select.appendChild(option); });
  }

  function init() {
    load();
    bind(); renderAll();
    var mode = window.STITCHCRAFT_DB && window.STITCHCRAFT_DB.mode === 'remote' ? 'Remote data' : 'Local data · saved in this browser';
    $('mode-badge').textContent = mode;
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true }); else init();
})();
