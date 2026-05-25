/**
 * s2-lk.js — S2 Lembar Kerja Main Controller
 *
 * Orkestrasi:
 *  1. Load status sidebar → build category tree
 *  2. Load worksheet untuk kategori terpilih
 *  3. Load rekap untuk parent kategori
 *  4. SSE: subscribe event → update sel spesifik tanpa reload seluruh tabel
 *  5. Controls: mode toggle ADHB/ADHK/Both/Compare
 */

'use strict';

// State
let _state = {
  wilayahKode:  '65',
  wilayahNama:  'Provinsi Kalimantan Utara',
  tahun:        new Date().getFullYear(),
  triwulan:     null,
  kategoriKode: null,
  mode:         WS_MODE.BOTH,
};

let _statusData   = {};
let _wsData       = null;
let _sseUnsubscribe = null;


// ── Init ──────────────────────────────────────────────────────────────────────

window.addEventListener('DOMContentLoaded', async () => {
  // Restore state from sessionStorage
  const saved = sessionStorage.getItem('simultan_filters');
  if (saved) {
    try {
      const f = JSON.parse(saved);
      _state.wilayahKode = f.wilayah_kode || '65';
      _state.wilayahNama = f.wilayah_nama || 'Provinsi Kalimantan Utara';
      _state.tahun       = f.tahun || new Date().getFullYear();
      _state.triwulan    = f.triwulan || null;
    } catch {}
  }

  // Connect SSE
  sse.connect();
  sse.on('cascade', onCascadeEvent);

  // Filter controls
  await initWilayahFilter(document.getElementById('filter-wilayah'), async () => {
    const sel = document.getElementById('filter-wilayah');
    _state.wilayahKode = sel.value;
    _state.wilayahNama = sel.options[sel.selectedIndex].text;
    await refreshAll();
  });

  initTahunFilter(document.getElementById('filter-tahun'), async () => {
    _state.tahun = parseInt(document.getElementById('filter-tahun').value);
    await refreshAll();
  });

  initTriwulanFilter(document.getElementById('filter-triwulan'), async () => {
    const v = document.getElementById('filter-triwulan').value;
    _state.triwulan = v === '' ? null : parseInt(v);
    await refreshAll();
  });

  // Mode toggles
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      _state.mode = btn.dataset.mode;
      if (_state.mode === WS_MODE.COMPARE) {
        loadCompareView();
      } else if (_wsData) {
        renderWorksheetView(_wsData, _state.mode);
      }
    });
  });

  // Print button
  document.getElementById('btn-print')?.addEventListener('click', () => window.print());

  // Sync filter dropdowns to _state
  _syncFilters();

  // Initial load
  await refreshAll();
});


// ── Sync filter dropdowns ─────────────────────────────────────────────────────

function _syncFilters() {
  // Tahun
  const tahunSel = document.getElementById('filter-tahun');
  if (tahunSel) {
    [...tahunSel.options].forEach(o => { if (parseInt(o.value) === _state.tahun) o.selected = true; });
  }
  // Triwulan
  const twSel = document.getElementById('filter-triwulan');
  if (twSel) {
    const val = _state.triwulan !== null ? String(_state.triwulan) : '';
    [...twSel.options].forEach(o => { o.selected = o.value === val; });
  }
}


// ── Data Loading ──────────────────────────────────────────────────────────────

async function refreshAll() {
  // Update title info
  _updateHeaderInfo();

  // Load status data untuk sidebar
  await loadStatus();

  // Jika ada kategori terpilih → reload worksheet
  if (_state.kategoriKode) {
    await loadWorksheet(_state.kategoriKode);
  } else {
    showPlaceholder();
  }
}

async function loadStatus() {
  try {
    _statusData = await getS2Status(_state.wilayahKode, _state.tahun, _state.triwulan);
    buildCatTree(_statusData, _state.kategoriKode, onCategorySelect);
  } catch (e) {
    console.warn('Status load error:', e);
  }
}

async function onCategorySelect(kode) {
  _state.kategoriKode = kode;
  // Update active in tree
  document.querySelectorAll('.cat-tree-item').forEach(el => {
    el.classList.toggle('active', el.dataset.kode === kode);
  });
  await loadWorksheet(kode);
}

async function loadWorksheet(kode) {
  if (!kode) return;

  // Show skeleton
  document.getElementById('ws-container').innerHTML = buildSkeletonHtml();
  document.getElementById('rekap-container').innerHTML = '';

  // Update header title
  const katInfo = _statusData[kode];
  if (katInfo) {
    document.getElementById('ws-kat-title').textContent = `${katInfo.kode} — ${katInfo.nama}`;
  }
  document.getElementById('ws-kat-title').textContent =
    katInfo ? `${katInfo.kode} — ${katInfo.nama}` : kode;

  try {
    // Load worksheet + rekap in parallel
    const parentKode = _statusData[kode]?.parent_kode;
    const [wsData, rekapData] = await Promise.all([
      getWorksheet(_state.wilayahKode, _state.tahun, _state.triwulan, kode),
      parentKode ? getRekap(_state.wilayahKode, _state.tahun, _state.triwulan, parentKode).catch(() => null) : null,
    ]);

    _wsData = wsData;

    // Render
    if (_state.mode === WS_MODE.COMPARE) {
      await loadCompareView();
    } else {
      renderWorksheetView(wsData, _state.mode);
    }
    if (rekapData) renderRekapSection(rekapData);

    // Update meta info
    _updateMetaInfo(wsData);

  } catch (e) {
    document.getElementById('ws-container').innerHTML = `
      <div class="lk-empty">
        <div class="icon">⚠️</div>
        <h3>Gagal Memuat Data</h3>
        <p>${e.message}</p>
        <button class="btn btn-ghost" onclick="loadWorksheet('${kode}')">Coba Lagi</button>
      </div>`;
    showToast('Gagal memuat worksheet: ' + e.message, 'error');
  }
}

async function loadCompareView() {
  document.getElementById('ws-container').innerHTML = buildSkeletonHtml();
  try {
    const parentKode = _state.kategoriKode
      ? (_statusData[_state.kategoriKode]?.parent_kode || '')
      : '';
    const data = await getCompare(_state.wilayahKode, _state.tahun, _state.triwulan, parentKode);
    const container = document.getElementById('ws-container');
    container.innerHTML = '';
    container.appendChild(buildSectionSep('COMPARE', { ..._state, tahun: _state.tahun, triwulan: _state.triwulan }));
    container.appendChild(buildCompareTable(data));
  } catch (e) {
    showToast('Gagal memuat compare: ' + e.message, 'error');
  }
}


// ── SSE Cascade Handler ───────────────────────────────────────────────────────

function onCascadeEvent(ev) {
  if (!_state.kategoriKode || !_wsData) return;

  updateStatusBar('calculating', 'Menerima update cascade...');

  if (ev.type === 'cascade_done') {
    updateStatusBar('done');
    showToast('Kalkulasi selesai — tabel diperbarui ✓', 'success', 2000);
    // Reload full worksheet untuk akurasi
    loadWorksheet(_state.kategoriKode);
    // Update sidebar status
    loadStatus();
    return;
  }

  // Targeted update jika event membawa data rows
  if (ev.rows && ev.rows.length > 0) {
    updateWorksheetCells(ev.rows);
    if (ev.subtotal) {
      ['adhb', 'adhk'].forEach(b => updateTotalRow(ev.subtotal, b));
    }
  }
}


// ── UI Helpers ────────────────────────────────────────────────────────────────

function showPlaceholder() {
  document.getElementById('ws-container').innerHTML = `
    <div class="lk-empty">
      <div class="icon">📋</div>
      <h3>Pilih Kategori</h3>
      <p>Klik salah satu kategori di sidebar kiri untuk menampilkan Lembar Kerja S2.</p>
    </div>`;
  document.getElementById('rekap-container').innerHTML = '';
}

function _updateHeaderInfo() {
  const periodeStr = _state.triwulan
    ? ['TW I', 'TW II', 'TW III', 'TW IV'][_state.triwulan - 1]
    : 'Tahunan';
  const el = document.getElementById('header-info-chip');
  if (el) el.textContent = `${_state.wilayahNama} · ${_state.tahun} · ${periodeStr}`;

  const titleEl = document.getElementById('sheet-title-block');
  if (titleEl) {
    titleEl.innerHTML = `
      <div class="title-row">
        <span class="t-label">Wilayah</span>
        <span class="t-value">${_state.wilayahNama}</span>
      </div>
      <hr class="t-divider">
      <div class="title-row">
        <span class="t-label">Tahun</span>
        <span class="t-value">${_state.tahun}</span>
        <span style="margin-left:16px" class="t-label">Periode</span>
        <span class="t-value">${periodeStr}</span>
      </div>`;
  }
}

function _updateMetaInfo(wsData) {
  const metaEl = document.getElementById('ws-meta');
  if (!metaEl || !wsData) return;
  const st = wsData.subtotal;
  const terisi = wsData.rows.filter(r => r.has_data).length;
  metaEl.innerHTML = `
    <span class="badge badge-gray">${terisi}/${wsData.komoditas_count} komoditas terisi</span>
    ${st?.ntb_adhb !== null && st?.ntb_adhb !== undefined
      ? `<span class="badge badge-blue">NTB ADHB: ${fmtJuta(st.ntb_adhb)} Juta Rp</span>`
      : ''}
    ${st?.ntb_adhk !== null && st?.ntb_adhk !== undefined
      ? `<span class="badge badge-green">NTB ADHK: ${fmtJuta(st.ntb_adhk)} Juta Rp</span>`
      : ''}
    ${st?.laju_pertumbuhan_pct !== null && st?.laju_pertumbuhan_pct !== undefined
      ? `<span class="badge ${parseFloat(st.laju_pertumbuhan_pct) >= 0 ? 'badge-green' : 'badge-red'}">${growthBadge(st.laju_pertumbuhan_pct)}</span>`
      : ''}
  `;
}

function buildSkeletonHtml() {
  const rows = Array.from({ length: 6 }, (_, i) => `
    <tr class="lk-row-normal">
      <td class="ctr" style="color:var(--text-light)">${i+1}</td>
      <td><div class="lk-skeleton-bar" style="width:${130+i*15}px"></div></td>
      ${Array.from({length: 13}, () => '<td><div class="lk-skeleton-bar" style="width:60px"></div></td>').join('')}
    </tr>`).join('');
  return `<div style="overflow-x:auto;border:1px solid var(--border);background:var(--surface);border-radius:var(--radius)">
    <table class="lk-worksheet-table" style="min-width:900px">
      <tbody>${rows}</tbody>
    </table>
  </div>`;
}
