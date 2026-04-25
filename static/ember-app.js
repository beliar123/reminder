'use strict';

/* ── State ── */
let currentUser = null;
let allEvents = [];
let selectedEventId = null;
let activeFilter = 'all';
let editingEventId = null;

/* ── Constants ── */
const CAT_META = {
  birthday:    { label: 'День рождения', color: 'var(--pink)' },
  anniversary: { label: 'Годовщина',     color: 'var(--violet)' },
  meeting:     { label: 'Встреча',       color: 'var(--yellow)' },
  personal:    { label: 'Личное',        color: 'var(--sage)' },
};

const RECURRENCE_LABELS = {
  one_time:        'Разовое',
  daily:           'Ежедневно',
  weekly:          'Еженедельно',
  monthly:         'Ежемесячно',
  every_6_months:  'Каждые 6 мес.',
  yearly:          'Ежегодно',
  every_18_months: 'Каждые 18 мес.',
  every_2_years:   'Каждые 2 года',
};

const FILTER_LABELS = {
  all:            'Все',
  upcoming:       'Предстоящие',
  completed:      'Завершённые',
  recurring:      'Повторяющиеся',
  'cat-birthday':    'Дни рождения',
  'cat-anniversary': 'Годовщины',
  'cat-meeting':     'Встречи',
  'cat-personal':    'Личные',
};

/* ── Utils ── */
function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatTime(dt) {
  return dt.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' });
}

function formatDate(dt) {
  return dt.toLocaleDateString('ru', { day: 'numeric', month: 'long', year: 'numeric' });
}

function formatDateShort(dt) {
  return dt.toLocaleDateString('ru', { day: 'numeric', month: 'short' });
}

function relativeDue(dt) {
  const diffMs = dt - new Date();
  if (diffMs < 0) {
    const mins = Math.round(-diffMs / 60000);
    if (mins < 60) return `просрочено на ${mins} мин`;
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return `просрочено на ${hrs} ч`;
    return `просрочено на ${Math.round(hrs / 24)} дн`;
  }
  const mins = Math.round(diffMs / 60000);
  if (mins < 60) return `через ${mins} мин`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `через ${hrs} ч`;
  return `через ${Math.round(hrs / 24)} дн`;
}

function toLocalISOString(d) {
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function groupByDay(events) {
  const map = new Map();
  for (const ev of events) {
    if (!ev.next_remind_at) continue;
    const dt = new Date(ev.next_remind_at);
    const key = dt.toDateString();
    if (!map.has(key)) map.set(key, { date: dt, events: [] });
    map.get(key).events.push(ev);
  }
  return [...map.values()].sort((a, b) => a.date - b.date);
}

/* ── Auth UI ── */
function showAuth() {
  document.getElementById('auth-overlay').style.display = 'flex';
  document.getElementById('app').classList.remove('visible');
}

function showApp() {
  document.getElementById('auth-overlay').style.display = 'none';
  document.getElementById('app').classList.add('visible');
}

document.querySelectorAll('.auth-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const which = tab.dataset.tab;
    document.getElementById('login-form').classList.toggle('hidden', which !== 'login');
    document.getElementById('register-form').classList.toggle('hidden', which !== 'register');
    document.getElementById('login-error').textContent = '';
    document.getElementById('register-error').textContent = '';
  });
});

document.getElementById('login-form').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = e.target.querySelector('button[type=submit]');
  const errEl = document.getElementById('login-error');
  errEl.textContent = '';
  btn.disabled = true;
  try {
    const res = await fetch(API + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('login-email').value,
        password: document.getElementById('login-password').value,
      }),
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.detail || 'Ошибка входа'; return; }
    saveTokens(data.access_token, data.refresh_token);
    await initApp();
  } catch {
    errEl.textContent = 'Ошибка соединения';
  } finally {
    btn.disabled = false;
  }
});

document.getElementById('register-form').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = e.target.querySelector('button[type=submit]');
  const errEl = document.getElementById('register-error');
  errEl.textContent = '';
  btn.disabled = true;
  try {
    const res = await fetch(API + '/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('reg-email').value,
        password: document.getElementById('reg-password').value,
        name: document.getElementById('reg-name').value || undefined,
      }),
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.detail || 'Ошибка регистрации'; return; }
    saveTokens(data.access_token, data.refresh_token);
    await initApp();
  } catch {
    errEl.textContent = 'Ошибка соединения';
  } finally {
    btn.disabled = false;
  }
});

document.getElementById('logout-btn').addEventListener('click', doLogout);
window.addEventListener('ember:logout', showAuth);

/* ── Filter logic ── */
function filterEvents(events, filter) {
  const now = new Date();
  switch (filter) {
    case 'upcoming':
      return events.filter(e => !e.is_completed && e.next_remind_at && new Date(e.next_remind_at) >= now);
    case 'completed':
      return events.filter(e => e.is_completed);
    case 'recurring':
      return events.filter(e => e.recurrence !== 'one_time');
    case 'cat-birthday':
      return events.filter(e => e.category === 'birthday');
    case 'cat-anniversary':
      return events.filter(e => e.category === 'anniversary');
    case 'cat-meeting':
      return events.filter(e => e.category === 'meeting');
    case 'cat-personal':
      return events.filter(e => e.category === 'personal');
    default:
      return events;
  }
}

function setFilter(filter) {
  activeFilter = filter;
  document.querySelectorAll('.nav-item[data-filter]').forEach(el => {
    el.classList.toggle('active', el.dataset.filter === filter);
  });
  document.querySelectorAll('.chip[data-chip]').forEach(el => {
    el.classList.toggle('on', el.dataset.chip === filter);
  });
  document.getElementById('crumb-filter').textContent = FILTER_LABELS[filter] || filter;
  renderTimeline(filterEvents(allEvents, filter));
}

document.querySelectorAll('.nav-item[data-filter]').forEach(el => {
  el.addEventListener('click', () => {
    setFilter(el.dataset.filter);
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('nav-overlay').classList.remove('open');
  });
});

document.querySelectorAll('.chip[data-chip]').forEach(el => {
  el.addEventListener('click', () => setFilter(el.dataset.chip));
});

/* ── Mobile nav ── */
document.getElementById('hamburger').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('nav-overlay').classList.toggle('open');
});

document.getElementById('nav-overlay').addEventListener('click', () => {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('nav-overlay').classList.remove('open');
});

/* ── Timeline render ── */
function nowLineHTML(now) {
  const hh = now.getHours().toString().padStart(2, '0');
  const mm = now.getMinutes().toString().padStart(2, '0');
  return `<div class="now-line">
    <div class="now-time">${hh}:${mm}</div>
    <div class="now-bullet"></div>
    <div style="display:flex;align-items:center;gap:0;flex:1">
      <div class="now-rule"></div>
      <span class="now-label">вы здесь</span>
    </div>
    <div></div>
  </div>`;
}

function itemHTML(ev, now) {
  const dt = new Date(ev.next_remind_at);
  const isPast = dt < now;
  const isSelected = ev.id === selectedEventId;
  const isUpcoming = !ev.is_completed && !isPast;
  const hh = dt.getHours().toString().padStart(2, '0');
  const mm = dt.getMinutes().toString().padStart(2, '0');
  const ampm = dt.getHours() < 12 ? 'AM' : 'PM';
  const catMeta = CAT_META[ev.category] || { label: ev.category, color: 'var(--bone-mute)' };
  const recLabel = ev.recurrence !== 'one_time' ? `↻ ${RECURRENCE_LABELS[ev.recurrence] || ev.recurrence}` : '';
  const dueLabel = ev.is_completed ? 'выполнено' : relativeDue(dt);
  const checkClass = ev.is_completed ? 'done' : (isUpcoming && Math.abs(dt - now) < 3600000 ? 'upcoming' : '');

  return `<article class="item${ev.is_completed ? ' done' : ''}${isSelected ? ' selected' : ''}" data-id="${ev.id}">
    <div class="item-time">${hh}:${mm}<span class="ampm"> ${ampm}</span></div>
    <div class="check ${checkClass}" data-check-id="${ev.id}"></div>
    <div class="item-body">
      <div class="h">${escHtml(ev.title)}</div>
      <div class="item-meta">
        <span class="meta-tag">
          <span class="d" style="background:${catMeta.color}"></span>
          ${catMeta.label}
        </span>
        ${recLabel ? `<span class="meta-recurrence">${recLabel}</span>` : ''}
      </div>
    </div>
    <div class="item-right">
      <span class="item-due">${dueLabel}</span>
    </div>
  </article>`;
}

function renderTimeline(events) {
  const container = document.getElementById('timeline-container');

  if (events.length === 0) {
    container.innerHTML = `<div class="empty-state">
      <div class="e-title">Тихо здесь.</div>
      <div class="e-sub">Нет напоминаний в этой категории</div>
    </div>`;
    return;
  }

  const now = new Date();
  const noDate = events.filter(e => !e.next_remind_at);
  const groups = groupByDay(events.filter(e => e.next_remind_at));
  let html = '';

  for (const group of groups) {
    const dayDate = new Date(group.date);
    const diffDays = Math.floor(
      (new Date(dayDate).setHours(0, 0, 0, 0) - new Date().setHours(0, 0, 0, 0)) / 86400000
    );
    const dayRel = diffDays === 0 ? 'сегодня' : diffDays === 1 ? 'завтра' : diffDays === -1 ? 'вчера' : '';
    const isToday = diffDays === 0;

    html += `<section class="day">
      <div class="day-head">
        <span class="day-num">${new Date(group.date).getDate()}</span>
        <span class="day-month">${new Date(group.date).toLocaleDateString('ru', { month: 'short', weekday: 'short' }).toUpperCase()}</span>
        ${dayRel ? `<span class="day-rel">${dayRel}</span>` : ''}
        <span class="day-line"></span>
      </div>`;

    const sorted = [...group.events].sort((a, b) => new Date(a.next_remind_at) - new Date(b.next_remind_at));
    let nowInserted = !isToday;

    for (const ev of sorted) {
      const dt = new Date(ev.next_remind_at);
      if (!nowInserted && dt >= now) {
        nowInserted = true;
        html += nowLineHTML(now);
      }
      html += itemHTML(ev, now);
    }

    if (!nowInserted) html += nowLineHTML(now);
    html += `</section>`;
  }

  if (noDate.length > 0) {
    html += `<section class="day">
      <div class="day-head">
        <span class="day-month" style="padding-left:0">БЕЗ ДАТЫ</span>
        <span class="day-line"></span>
      </div>`;
    for (const ev of noDate) {
      const isSelected = ev.id === selectedEventId;
      const catMeta = CAT_META[ev.category] || { label: ev.category, color: 'var(--bone-mute)' };
      html += `<article class="item${ev.is_completed ? ' done' : ''}${isSelected ? ' selected' : ''}" data-id="${ev.id}">
        <div class="item-time">—</div>
        <div class="check ${ev.is_completed ? 'done' : ''}" data-check-id="${ev.id}"></div>
        <div class="item-body">
          <div class="h">${escHtml(ev.title)}</div>
          <div class="item-meta">
            <span class="meta-tag"><span class="d" style="background:${catMeta.color}"></span>${catMeta.label}</span>
          </div>
        </div>
        <div class="item-right"></div>
      </article>`;
    }
    html += `</section>`;
  }

  container.innerHTML = html;

  container.querySelectorAll('.item').forEach(el => {
    el.addEventListener('click', e => {
      if (e.target.closest('.check')) return;
      selectEvent(parseInt(el.dataset.id));
    });
  });

  container.querySelectorAll('.check[data-check-id]').forEach(el => {
    el.addEventListener('click', e => {
      e.stopPropagation();
      handleCheckClick(parseInt(el.dataset.checkId));
    });
  });
}

/* ── Check / complete ── */
async function handleCheckClick(eventId) {
  const ev = allEvents.find(e => e.id === eventId);
  if (!ev || ev.is_completed) return;

  const histRes = await apiFetch(`/events/${eventId}/history`);
  if (!histRes || !histRes.ok) return;
  const histData = await histRes.json();
  const pending = histData.items.find(h => !h.completed_at);
  if (!pending) return;

  const res = await apiFetch(`/events/${eventId}/history/${pending.id}/complete`, {
    method: 'POST',
    body: JSON.stringify({ notes: null }),
  });
  if (res && res.ok) {
    await loadEvents();
    if (selectedEventId === eventId) renderDetail(allEvents.find(e => e.id === eventId));
  }
}

/* ── Detail rail ── */
function selectEvent(id) {
  selectedEventId = id;
  const ev = allEvents.find(e => e.id === id);
  if (!ev) return;
  renderTimeline(filterEvents(allEvents, activeFilter));
  renderDetail(ev);
  if (window.innerWidth <= 1100) {
    document.getElementById('detail-rail').classList.add('mobile-open');
  }
}

async function renderDetail(ev) {
  const emptyEl = document.getElementById('detail-empty');
  const contentEl = document.getElementById('detail-content');

  if (!ev) {
    emptyEl.style.display = 'flex';
    contentEl.style.display = 'none';
    return;
  }

  emptyEl.style.display = 'none';
  contentEl.style.display = 'flex';

  const dt = ev.next_remind_at ? new Date(ev.next_remind_at) : null;
  const pill = document.getElementById('detail-pill');

  if (ev.is_completed) {
    pill.textContent = '✓ выполнено';
    pill.className = 'pill done';
  } else {
    pill.textContent = `● ${dt ? relativeDue(dt) : 'без даты'}`;
    pill.className = 'pill';
  }

  document.getElementById('detail-title').textContent = ev.title;
  const noteEl = document.getElementById('detail-note');
  noteEl.style.display = ev.description ? '' : 'none';
  if (ev.description) noteEl.textContent = ev.description;

  const whenEl = document.getElementById('detail-when');
  whenEl.innerHTML = dt
    ? `${formatDate(dt)} · <span class="accent">${formatTime(dt)}</span>`
    : '<span class="muted">не указана</span>';

  const catMeta = CAT_META[ev.category] || { label: ev.category, color: 'var(--bone-mute)' };
  document.getElementById('detail-category').innerHTML =
    `<span style="width:8px;height:8px;border-radius:50%;background:${catMeta.color};display:inline-block;flex-shrink:0"></span>${catMeta.label}`;

  document.getElementById('detail-recurrence').innerHTML =
    ev.recurrence === 'one_time'
      ? `<span class="muted">разовое</span>`
      : `<span style="color:var(--violet)">${RECURRENCE_LABELS[ev.recurrence] || ev.recurrence}</span>`;

  document.getElementById('detail-created').textContent = formatDate(new Date(ev.created_at));

  document.getElementById('detail-edit-btn').dataset.id = ev.id;
  document.getElementById('detail-delete-btn').dataset.id = ev.id;

  loadDetailHistory(ev.id);
}

async function loadDetailHistory(eventId) {
  const listEl = document.getElementById('detail-history-list');
  listEl.innerHTML = '<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;color:var(--bone-faint)">Загрузка…</div>';

  const res = await apiFetch(`/events/${eventId}/history?limit=10`);
  if (!res || !res.ok) {
    listEl.innerHTML = '<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;color:var(--bone-faint)">Нет данных</div>';
    return;
  }
  const data = await res.json();

  if (!data.items || data.items.length === 0) {
    listEl.innerHTML = '<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;color:var(--bone-faint)">История пуста</div>';
    return;
  }

  listEl.innerHTML = data.items.map(h => {
    const sched = new Date(h.scheduled_at);
    const isCompleted = !!h.completed_at;
    const completedAt = isCompleted ? new Date(h.completed_at) : null;
    return `<div class="history-item">
      <span class="ts">${formatDateShort(sched)}</span>
      <span class="status-dot ${isCompleted ? 'completed' : 'pending'}"></span>
      <span style="flex:1">
        ${isCompleted
          ? `Выполнено ${formatTime(completedAt)}${h.notes ? ` — <em style="color:var(--bone-dim)">${escHtml(h.notes)}</em>` : ''}`
          : `Запланировано · ${formatTime(sched)}`
        }
      </span>
      ${!isCompleted
        ? `<button class="history-complete-btn" data-event-id="${eventId}" data-history-id="${h.id}">Выполнить</button>`
        : ''
      }
    </div>`;
  }).join('');

  listEl.querySelectorAll('.history-complete-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      const res = await apiFetch(`/events/${btn.dataset.eventId}/history/${btn.dataset.historyId}/complete`, {
        method: 'POST',
        body: JSON.stringify({ notes: null }),
      });
      if (res && res.ok) {
        await loadEvents();
        const ev = allEvents.find(e => e.id === parseInt(btn.dataset.eventId));
        if (ev) renderDetail(ev);
      }
    });
  });
}

/* ── Edit / Delete ── */
document.getElementById('detail-edit-btn').addEventListener('click', () => {
  openEditModal(parseInt(document.getElementById('detail-edit-btn').dataset.id));
});

document.getElementById('detail-delete-btn').addEventListener('click', () => {
  const id = parseInt(document.getElementById('detail-delete-btn').dataset.id);
  const ev = allEvents.find(e => e.id === id);
  if (!ev) return;
  document.getElementById('delete-modal-text').textContent = `«${ev.title}» будет удалено безвозвратно.`;
  document.getElementById('delete-confirm').dataset.id = id;
  document.getElementById('delete-modal').classList.remove('hidden');
});

document.getElementById('delete-modal-close').addEventListener('click', () => {
  document.getElementById('delete-modal').classList.add('hidden');
});

document.getElementById('delete-cancel').addEventListener('click', () => {
  document.getElementById('delete-modal').classList.add('hidden');
});

document.getElementById('delete-confirm').addEventListener('click', async () => {
  const id = parseInt(document.getElementById('delete-confirm').dataset.id);
  const res = await apiFetch(`/events/${id}`, { method: 'DELETE' });
  if (res && (res.ok || res.status === 204)) {
    document.getElementById('delete-modal').classList.add('hidden');
    selectedEventId = null;
    renderDetail(null);
    await loadEvents();
  }
});

/* ── Create / Edit modal ── */
document.getElementById('open-create-btn').addEventListener('click', openCreateModal);

function openCreateModal() {
  editingEventId = null;
  document.getElementById('modal-title').textContent = 'Новое напоминание';
  document.getElementById('modal-submit').textContent = 'Создать';
  document.getElementById('event-form').reset();
  document.getElementById('ef-datetime').value = toLocalISOString(new Date(Date.now() + 3600000));
  document.getElementById('modal-error').textContent = '';
  document.getElementById('event-modal').classList.remove('hidden');
}

function openEditModal(id) {
  const ev = allEvents.find(e => e.id === id);
  if (!ev) return;
  editingEventId = id;
  document.getElementById('modal-title').textContent = 'Редактировать';
  document.getElementById('modal-submit').textContent = 'Сохранить';
  document.getElementById('ef-title').value = ev.title;
  document.getElementById('ef-desc').value = ev.description || '';
  document.getElementById('ef-category').value = ev.category;
  document.getElementById('ef-recurrence').value = ev.recurrence;
  document.getElementById('ef-datetime').value = ev.next_remind_at
    ? toLocalISOString(new Date(ev.next_remind_at)) : '';
  document.getElementById('modal-error').textContent = '';
  document.getElementById('event-modal').classList.remove('hidden');
}

document.getElementById('modal-close').addEventListener('click', () => {
  document.getElementById('event-modal').classList.add('hidden');
});

document.getElementById('event-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('event-modal'))
    document.getElementById('event-modal').classList.add('hidden');
});

document.getElementById('event-form').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = document.getElementById('modal-submit');
  const errEl = document.getElementById('modal-error');
  errEl.textContent = '';
  btn.disabled = true;

  const body = {
    title: document.getElementById('ef-title').value.trim(),
    description: document.getElementById('ef-desc').value.trim() || null,
    category: document.getElementById('ef-category').value,
    recurrence: document.getElementById('ef-recurrence').value,
    next_remind_at: new Date(document.getElementById('ef-datetime').value).toISOString(),
  };

  try {
    const res = editingEventId
      ? await apiFetch(`/events/${editingEventId}`, { method: 'PATCH', body: JSON.stringify(body) })
      : await apiFetch('/events', { method: 'POST', body: JSON.stringify(body) });

    if (!res || !res.ok) {
      const data = res ? await res.json() : {};
      errEl.textContent = data.detail || 'Ошибка сохранения';
      return;
    }
    document.getElementById('event-modal').classList.add('hidden');
    await loadEvents();
  } catch {
    errEl.textContent = 'Ошибка соединения';
  } finally {
    btn.disabled = false;
  }
});

/* ── Counts ── */
function updateCounts() {
  const now = new Date();
  const total = allEvents.length;
  const upcoming = allEvents.filter(e => !e.is_completed && e.next_remind_at && new Date(e.next_remind_at) >= now).length;
  const completed = allEvents.filter(e => e.is_completed).length;
  const recurring = allEvents.filter(e => e.recurrence !== 'one_time').length;

  document.getElementById('stat-total').innerHTML = `<em>${total}</em>`;
  document.getElementById('stat-upcoming').textContent = upcoming;
  document.getElementById('stat-completed').textContent = completed;

  document.getElementById('nav-count-all').textContent = total;
  document.getElementById('nav-count-upcoming').textContent = upcoming;
  document.getElementById('nav-count-completed').textContent = completed;
  document.getElementById('nav-count-recurring').textContent = recurring;
  document.getElementById('nav-count-birthday').textContent = allEvents.filter(e => e.category === 'birthday').length;
  document.getElementById('nav-count-anniversary').textContent = allEvents.filter(e => e.category === 'anniversary').length;
  document.getElementById('nav-count-meeting').textContent = allEvents.filter(e => e.category === 'meeting').length;
  document.getElementById('nav-count-personal').textContent = allEvents.filter(e => e.category === 'personal').length;

  document.getElementById('chip-all-ct').textContent = total;
  document.getElementById('chip-upcoming-ct').textContent = upcoming;
  document.getElementById('chip-recurring-ct').textContent = recurring;
  document.getElementById('chip-completed-ct').textContent = completed;
}

async function loadEvents() {
  const res = await apiFetch('/events');
  if (!res || !res.ok) return;
  allEvents = await res.json();
  updateCounts();
  renderTimeline(filterEvents(allEvents, activeFilter));
}

/* ── Greeting ── */
function renderGreeting(user) {
  const h = new Date().getHours();
  const greet = h < 6 ? 'Доброй ночи' : h < 12 ? 'Доброе утро' : h < 18 ? 'Добрый день' : 'Добрый вечер';
  const name = user?.name || user?.email?.split('@')[0] || '';
  document.getElementById('greeting-title').innerHTML = `${escHtml(greet)}, ${escHtml(name)} <em>—</em>`;
  const dateStr = new Date().toLocaleDateString('ru', { weekday: 'long', day: 'numeric', month: 'long' });
  document.getElementById('greeting-sub').innerHTML = `Сегодня <span class="accent">${dateStr}</span>.`;
}

/* ── Keyboard shortcuts ── */
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.getElementById('event-modal').classList.add('hidden');
    document.getElementById('delete-modal').classList.add('hidden');
    document.getElementById('detail-rail').classList.remove('mobile-open');
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('nav-overlay').classList.remove('open');
  }
  if (e.key === 'n' && !e.ctrlKey && !e.metaKey
    && document.activeElement.tagName !== 'INPUT'
    && document.activeElement.tagName !== 'TEXTAREA') {
    openCreateModal();
  }
});

/* ── Init ── */
async function initApp() {
  const userRes = await apiFetch('/users/me');
  if (!userRes || !userRes.ok) { showAuth(); return; }
  currentUser = await userRes.json();

  document.getElementById('user-avatar').textContent =
    (currentUser.name || currentUser.email || '?').slice(0, 1).toUpperCase();
  document.getElementById('user-name').textContent = currentUser.name || currentUser.email;

  renderGreeting(currentUser);
  showApp();
  await loadEvents();
  setInterval(loadEvents, 60000);
}

/* ── Boot ── */
if (accessToken) {
  initApp();
} else {
  showAuth();
}
