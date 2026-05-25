/**
 * mdm-utils.js — MDM Shared Utilities
 */
'use strict';

// ── User Identity ────────────────────────────────────────────────────────────────────────────

function getMdmUser() {
  return sessionStorage.getItem('mdm_user') || 'Admin';
}
function setMdmUser(nama) {
  sessionStorage.setItem('mdm_user', nama);
}

// ── Toast Notification (MDM specific) ───────────────────────────────────────

function mdmToast(msg, type = 'success', duration = 3500) {
  let el = document.getElementById('mdm-toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'mdm-toast';
    el.style.cssText = `
      position:fixed; bottom:24px; right:24px; z-index:9999;
      background:#1E293B; color:#fff; padding:12px 18px;
      border-radius:8px; font-size:0.83rem; max-width:380px;
      box-shadow:0 8px 24px rgba(0,0,0,0.25);
      transform:translateY(80px); opacity:0;
      transition:all 0.3s cubic-bezier(0.4,0,0.2,1);
      display:flex; align-items:center; gap:10px;
    `;
    document.body.appendChild(el);
  }
  const icons = { success:'✅', error:'❌', warning:'⚠️', info:'ℹ️' };
  const colors = { success:'#059669', error:'#E74C3C', warning:'#D97706', info:'#2563EB' };
  el.style.borderLeft = `4px solid ${colors[type] || colors.info}`;
  el.innerHTML = `<span>${icons[type] || ''}</span><span>${msg}</span>`;
  el.style.transform = 'translateY(0)';
  el.style.opacity = '1';
  clearTimeout(el._timeout);
  el._timeout = setTimeout(() => {
    el.style.transform = 'translateY(80px)';
    el.style.opacity = '0';
  }, duration);
}

// ── Confirm with Reason Modal ───────────────────────────────────────────────────

function mdmConfirmWithReason({ title, message, requireReason = false, onConfirm }) {
  let overlay = document.getElementById('mdm-confirm-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'mdm-confirm-overlay';
    overlay.className = 'mdm-modal-overlay';
    overlay.innerHTML = `
      <div class="mdm-modal">
        <div class="mdm-modal-header">
          <span class="icon">⚠️</span>
          <span class="mdm-modal-title" id="_cm-title"></span>
        </div>
        <div class="mdm-modal-body">
          <p id="_cm-msg" style="font-size:0.84rem;line-height:1.6;margin:0"></p>
          <div class="mdm-reason-input" id="_cm-reason-wrap">
            <label>Alasan perubahan <span style="color:#E74C3C">*</span></label>
            <textarea id="_cm-reason" placeholder="Jelaskan alasan perubahan ini..."></textarea>
          </div>
        </div>
        <div class="mdm-modal-footer">
          <button class="btn btn-ghost" id="_cm-cancel">Batal</button>
          <button class="btn btn-danger" id="_cm-ok">Ya, Lanjutkan</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
  }

  document.getElementById('_cm-title').textContent = title || 'Konfirmasi';
  document.getElementById('_cm-msg').innerHTML = message || '';
  document.getElementById('_cm-reason-wrap').style.display = requireReason ? 'block' : 'none';
  document.getElementById('_cm-reason').value = '';

  overlay.classList.add('open');

  const close = () => overlay.classList.remove('open');

  document.getElementById('_cm-cancel').onclick = close;
  overlay.onclick = (e) => { if (e.target === overlay) close(); };
  document.getElementById('_cm-ok').onclick = () => {
    const reason = document.getElementById('_cm-reason').value.trim();
    if (requireReason && !reason) {
      document.getElementById('_cm-reason').style.borderColor = '#E74C3C';
      return;
    }
    close();
    onConfirm(reason);
  };
}

// ── Drawer Helper ────────────────────────────────────────────────────────────────────

function openDrawer(drawerId, overlayId) {
  document.getElementById(drawerId)?.classList.add('open');
  const ov = document.getElementById(overlayId);
  if (ov) { ov.classList.add('open'); ov.onclick = (e) => { if (e.target === ov) closeDrawer(drawerId, overlayId); }; }
}
function closeDrawer(drawerId, overlayId) {
  document.getElementById(drawerId)?.classList.remove('open');
  document.getElementById(overlayId)?.classList.remove('open');
}

// ── KBLI Validation ─────────────────────────────────────────────────────────────────

function validateKbliFormat(kode) {
  if (!kode) return null; // empty is ok (not required)
  // KBLI: 5 digit numerik, opsional suffix huruf
  return /^\d{5}[A-Z]?$/.test(kode.trim().toUpperCase());
}
function applyKbliValidation(input) {
  const val = input.value.trim();
  if (!val) { input.classList.remove('kbli-valid', 'kbli-invalid'); return; }
  const ok = validateKbliFormat(val);
  input.classList.toggle('kbli-valid', ok);
  input.classList.toggle('kbli-invalid', !ok);
}

// ── Format Helpers ─────────────────────────────────────────────────────────────

function fmtDate(isoStr) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  return d.toLocaleDateString('id-ID', { year:'numeric', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' });
}
function fmtBool(val) {
  if (val === null || val === undefined) return '<span style="color:#9CA3AF">-</span>';
  return val
    ? '<span class="status-badge aktif">✓ Ya</span>'
    : '<span class="status-badge nonaktif">× Tidak</span>';
}
function fmtStatus(aktif) {
  return aktif
    ? '<span class="status-badge aktif">✓ Aktif</span>'
    : '<span class="status-badge nonaktif">○ Nonaktif</span>';
}
function fmtKode(val) {
  if (!val) return '<span style="color:#9CA3AF;font-size:0.72rem">-</span>';
  return `<code style="background:#F1F5F9;padding:1px 5px;border-radius:3px;font-size:0.78rem">${val}</code>`;
}
function fmtFaktor(val) {
  if (val === null || val === undefined) return '—';
  return `<span class="faktor-val">${parseFloat(val).toFixed(3)}</span><span class="faktor-pct"></span>`;
}

// ── Diff Renderer (for import preview) ───────────────────────────────────────

function renderDiffDetail(diffs) {
  if (!diffs || diffs.length === 0) return '';
  return diffs.map(d => `
    <div style="font-size:0.73rem;margin:2px 0">
      <span style="color:#6B7280">${d.kolom}:</span>
      <span class="diff-cell-old">${d.lama || '—'}</span>
      →
      <span class="diff-cell-new">${d.baru || '—'}</span>
    </div>
  `).join('');
}

// ── Tab Helper ──────────────────────────────────────────────────────────────────────────

function initMdmTabs(containerSelector) {
  const container = document.querySelector(containerSelector);
  if (!container) return;
  const btns = container.querySelectorAll('.mdm-tab-btn');
  const panels = container.querySelectorAll('.mdm-tab-panel');
  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      btns.forEach(b => b.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const target = btn.dataset.tab;
      container.querySelector(`#${target}`)?.classList.add('active');
    });
  });
  // Activate first tab by default
  if (btns[0]) btns[0].click();
}
