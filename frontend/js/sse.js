/**
 * sse.js — SSE Client & Cascade Event Bus
 * Mengelola koneksi Server-Sent Events dari /api/events.
 * Broadcast event ke listener yang terdaftar.
 */

class CascadeSSE {
  constructor() {
    this._es = null;
    this._listeners = {};     // { eventType: [fn, ...] }
    this._taskListeners = {}; // { task_id: fn }
    this._reconnectDelay = 2000;
    this._connected = false;
  }

  connect() {
    if (this._es) return;
    this._es = new EventSource('/api/events');

    this._es.addEventListener('connected', (e) => {
      this._connected = true;
      this._reconnectDelay = 2000;
      console.log('[SSE] Connected');
      this._emit('connected', JSON.parse(e.data));
      updateStatusBar('connected');
    });

    this._es.addEventListener('cascade', (e) => {
      const ev = JSON.parse(e.data);
      console.log('[SSE] cascade:', ev);
      this._emit('cascade', ev);
      if (ev.task_id && this._taskListeners[ev.task_id]) {
        this._taskListeners[ev.task_id](ev);
      }
    });

    this._es.addEventListener('heartbeat', () => {
      // Koneksi masih hidup
    });

    this._es.addEventListener('timeout', () => {
      this.disconnect();
      setTimeout(() => this.connect(), 1000);
    });

    this._es.onerror = () => {
      this._connected = false;
      updateStatusBar('disconnected');
      console.warn('[SSE] Connection error, reconnecting...');
      this.disconnect();
      setTimeout(() => {
        this._reconnectDelay = Math.min(this._reconnectDelay * 1.5, 30000);
        this.connect();
      }, this._reconnectDelay);
    };
  }

  disconnect() {
    if (this._es) {
      this._es.close();
      this._es = null;
      this._connected = false;
    }
  }

  on(eventType, fn) {
    if (!this._listeners[eventType]) this._listeners[eventType] = [];
    this._listeners[eventType].push(fn);
    return () => this.off(eventType, fn); // returns unsubscribe fn
  }

  off(eventType, fn) {
    if (!this._listeners[eventType]) return;
    this._listeners[eventType] = this._listeners[eventType].filter(f => f !== fn);
  }

  onTask(taskId, fn) {
    this._taskListeners[taskId] = fn;
    return () => { delete this._taskListeners[taskId]; };
  }

  _emit(eventType, data) {
    (this._listeners[eventType] || []).forEach(fn => fn(data));
  }
}

// Singleton
const sse = new CascadeSSE();


// ── Toast Notifications ───────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icons = { success: '✓', error: '✕', warn: '⚠', info: 'ℹ' };
  toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'slideIn 200ms ease reverse';
    setTimeout(() => toast.remove(), 200);
  }, duration);
}


// ── Status Bar ────────────────────────────────────────────────────────────────
function updateStatusBar(state, message = '') {
  const indicator = document.querySelector('.status-indicator');
  const statusText = document.querySelector('.status-text');
  if (!indicator) return;
  indicator.className = 'status-indicator';
  if (state === 'calculating') {
    indicator.classList.add('calculating');
    if (statusText) statusText.textContent = message || 'Sedang menghitung...';
  } else if (state === 'done') {
    indicator.classList.add('done');
    if (statusText) statusText.textContent = message || 'Kalkulasi selesai';
    setTimeout(() => {
      indicator.classList.remove('done');
      if (statusText) statusText.textContent = 'Siap';
    }, 3000);
  } else if (state === 'disconnected') {
    if (statusText) statusText.textContent = 'SSE terputus — mencoba reconnect...';
  } else {
    if (statusText) statusText.textContent = 'Siap';
  }
}


// ── Row spinner helpers ───────────────────────────────────────────────────────
function setRowUpdating(row, taskId) {
  if (!row) return;
  row.classList.remove('row-empty', 'row-filled', 'row-updated');
  row.classList.add('row-updating');

  if (taskId) {
    const unsub = sse.onTask(taskId, (ev) => {
      if (ev.type === 'cascade_done' || ev.type === 'cascade_error') {
        setRowDone(row, ev.type === 'cascade_done');
        unsub();
      }
    });
  }
}

function setRowDone(row, success = true) {
  if (!row) return;
  row.classList.remove('row-updating', 'row-empty');
  if (success) {
    row.classList.add('row-filled', 'row-updated');
    // Animasi fade ke putih terjadi di CSS; setelah 2.1s bersihkan
    setTimeout(() => row.classList.remove('row-updated'), 2200);
  } else {
    row.classList.add('row-empty');
    showToast('Kalkulasi gagal — periksa data.', 'error');
  }
}

function getRowState(row) {
  const inputs = row.querySelectorAll('.cell-input:not([readonly]):not([disabled])');
  const hasAny = [...inputs].some(inp => inp.value.trim() !== '');
  return hasAny ? 'filled' : 'empty';
}

function refreshRowState(row) {
  const state = getRowState(row);
  row.classList.remove('row-empty', 'row-filled', 'row-updated', 'row-updating');
  row.classList.add(`row-${state}`);
}
