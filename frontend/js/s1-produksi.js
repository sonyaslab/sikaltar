/**
 * s1-produksi.js — S1.P Input Produksi Logic
 *
 * Fitur utama:
 *  - Tampilkan/sembunyikan sub-baris TW1–TW4 per komoditas
 *  - Deteksi konflik: data tahunan langsung VS sum triwulan
 *  - Badge status: Sementara / Tetap / Data Tahunan Langsung
 *  - Auto-save on blur + cascade trigger
 */

let _hierarki = [];
let _produksiMap = {};   // { komoditas_id: rowData }
let _showTw = false;

window.addEventListener('DOMContentLoaded', async () => {
  sse.connect();

  await initWilayahFilter(document.getElementById('filter-wilayah'), reloadData);
  initTahunFilter(document.getElementById('filter-tahun'), reloadData);
  initTriwulanFilter(document.getElementById('filter-triwulan'), reloadData);

  document.getElementById('show-tw').addEventListener('change', (e) => {
    _showTw = e.target.checked;
    toggleTwRows();
  });

  document.getElementById('btn-refresh').addEventListener('click', reloadData);
  document.getElementById('btn-export').addEventListener('click', () =>
    showToast('Export Excel akan segera tersedia.', 'warn'));

  sse.on('cascade', (ev) => {
    if (ev.type === 'cascade_done') updateStatusBar('done');
  });

  await loadHierarki();
  await reloadData();
});

async function loadHierarki() {
  try { _hierarki = await getHierarki(); }
  catch (e) { showToast('Gagal memuat hierarki: ' + e.message, 'error'); }
}

async function reloadData() {
  const f = getApiParams();
  document.getElementById('filter-info').textContent =
    `${getFilters().wilayah_nama} · ${f.tahun}${f.triwulan ? ' · TW'+f.triwulan : ' · Tahunan'}`;
  document.getElementById('produksi-tbody').innerHTML =
    `<tr><td colspan="8" class="table-empty-msg"><div class="spinner" style="margin:0 auto"></div></td></tr>`;

  try {
    const data = await getProduksi(f.wilayah_kode, f.tahun, f.triwulan);
    _produksiMap = {};
    data.forEach(r => { _produksiMap[r.komoditas_id] = r; });
    renderTable();
    document.getElementById('last-update').textContent =
      'Dimuat: ' + new Date().toLocaleTimeString('id-ID');
  } catch (e) {
    showToast('Gagal memuat: ' + e.message, 'error');
    document.getElementById('produksi-tbody').innerHTML =
      `<tr><td colspan="8" class="table-empty-msg"><div class="icon">⚠️</div>Gagal memuat.</td></tr>`;
  }
}

function renderTable() {
  const tbody = document.getElementById('produksi-tbody');
  tbody.innerHTML = '';
  let rowNo = 0;

  function renderKategori(node, depth = 0) {
    const tr = document.createElement('tr');
    if (depth === 0) {
      tr.className = 'row-cat-header';
      tr.innerHTML = `<td colspan="8"><span class="cat-code">${node.kode}</span>${node.nama}</td>`;
    } else {
      tr.className = depth === 1 ? 'row-subcat' : 'row-subcat-2';
      tr.innerHTML = `
        <td class="col-no"></td>
        <td colspan="7" style="padding-left:${16+depth*12}px">
          <span class="sub-code">${node.kode}</span>${node.nama}
        </td>`;
    }
    tbody.appendChild(tr);

    (node.komoditas || []).forEach(kom => {
      rowNo++;
      const { mainRow, twRow } = buildKomoditasRow(kom, rowNo);
      tbody.appendChild(mainRow);
      if (twRow) {
        twRow.style.display = _showTw ? '' : 'none';
        tbody.appendChild(twRow);
      }
    });

    (node.children || []).forEach(child => renderKategori(child, depth + 1));
  }

  _hierarki.forEach(root => renderKategori(root, 0));

  if (rowNo === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="table-empty-msg">
      <div class="icon">🌾</div>Belum ada komoditas.</td></tr>`;
  }
}

function buildKomoditasRow(kom, rowNo) {
  const d = _produksiMap[kom.id] || {};
  const hasData = d.kuantum !== null && d.kuantum !== undefined;
  const hasConflict = d.has_conflict;
  const hasTwData = d.tw1 || d.tw2 || d.tw3 || d.tw4;
  const f = getFilters();

  // Status badge
  let statusBadge = '';
  if (d.triwulan === null && hasData) {
    statusBadge = '<span class="badge badge-yellow">Tahunan Langsung</span>';
  } else if (d.status === 'tetap') {
    statusBadge = '<span class="badge badge-blue">Tetap</span>';
  } else if (hasData) {
    statusBadge = '<span class="badge badge-gray">Sementara</span>';
  }

  // Conflict badge
  const conflictBadge = hasConflict
    ? `<span class="conflict-badge" title="Data tahunan manual tersimpan. Sistem menggunakan jumlah triwulan.">⚠ Konflik TW</span>`
    : '';

  const mainRow = document.createElement('tr');
  mainRow.className = `row-komoditas ${hasData ? 'row-filled' : 'row-empty'}${hasConflict ? ' row-empty' : ''}`;
  mainRow.dataset.komoditasId = kom.id;
  mainRow.dataset.hasTw = hasTwData ? '1' : '0';

  mainRow.innerHTML = `
    <td class="col-no">${rowNo}</td>
    <td>
      <div class="kom-nama">${kom.nama}</div>
      <div class="kom-wujud">${hasTwData ? '<span style="font-size:0.72rem;color:var(--text-muted)">▾ Ada data triwulan</span>' : ''}</div>
    </td>
    <td style="font-size:0.78rem;color:var(--text-muted)">${kom.wujud_produksi || '—'}</td>
    <td style="font-size:0.78rem;color:var(--text-muted)">${kom.satuan_produksi || '—'}</td>
    <td class="num-right">
      <input type="number" class="cell-input" data-field="kuantum" data-kom="${kom.id}"
        value="${d.kuantum !== null && d.kuantum !== undefined ? d.kuantum : ''}" 
        placeholder="0" min="0" step="0.001">
      ${conflictBadge}
    </td>
    <td>${statusBadge}</td>
    <td>
      <select class="cell-select" data-field="sumber_data" data-kom="${kom.id}">
        ${SUMBER_DATA_OPTIONS.map(s =>
          `<option value="${s}" ${d.sumber_data === s ? 'selected':''}>${s||'— Pilih —'}</option>`
        ).join('')}
      </select>
    </td>
    <td class="col-action" id="pstatus-${kom.id}" style="text-align:center">
      ${hasData && !hasConflict ? '<span style="color:var(--success)">✓</span>' : ''}
    </td>
  `;

  // Events on main row
  const input = mainRow.querySelector('.cell-input');
  input.addEventListener('blur', () => onProduksiBlur(mainRow, input));
  input.addEventListener('focus', () => input.select());
  const sel = mainRow.querySelector('.cell-select');
  if (sel) sel.addEventListener('change', () => onProduksiBlur(mainRow, sel));

  // TW breakdown row
  let twRow = null;
  if (hasTwData || f.triwulan === null) {
    twRow = buildTwRow(kom, d);
  }

  return { mainRow, twRow };
}

function buildTwRow(kom, d) {
  const twRow = document.createElement('tr');
  twRow.className = 'row-tw-breakdown';
  twRow.dataset.komId = kom.id;

  const totalTw = d.total_tw
    ? parseFloat(d.total_tw).toLocaleString('id-ID', { maximumFractionDigits: 3 })
    : '—';

  const makeTwCell = (tw, val) => `
    <div class="tw-cell">
      <label>TW${tw}</label>
      <input type="number" class="tw-input" data-tw="${tw}" data-kom="${kom.id}"
        value="${val !== null && val !== undefined ? val : ''}" placeholder="—" min="0" step="0.001">
    </div>`;

  twRow.innerHTML = `
    <td colspan="8">
      <div class="tw-group">
        ${makeTwCell(1, d.tw1)}
        ${makeTwCell(2, d.tw2)}
        ${makeTwCell(3, d.tw3)}
        ${makeTwCell(4, d.tw4)}
        <div class="tw-cell">
          <label class="tw-total-label">TOTAL</label>
          <span class="tw-total" id="tw-total-${kom.id}">${totalTw}</span>
          <span style="font-size:0.73rem;color:var(--text-muted)">${kom.satuan_produksi || ''}</span>
        </div>
      </div>
    </td>`;

  // Events for each TW input
  twRow.querySelectorAll('.tw-input').forEach(inp => {
    inp.addEventListener('blur', () => onTwBlur(kom, inp));
    inp.addEventListener('focus', () => inp.select());
    inp.addEventListener('input', () => updateTwTotal(kom.id));
  });

  return twRow;
}

function updateTwTotal(komId) {
  const twInputs = document.querySelectorAll(`.tw-input[data-kom="${komId}"]`);
  let total = 0;
  twInputs.forEach(inp => {
    const v = parseFloat(inp.value);
    if (!isNaN(v)) total += v;
  });
  const totalEl = document.getElementById(`tw-total-${komId}`);
  if (totalEl) totalEl.textContent = total > 0
    ? total.toLocaleString('id-ID', { maximumFractionDigits: 3 }) : '—';
}

function toggleTwRows() {
  document.querySelectorAll('.row-tw-breakdown').forEach(row => {
    row.style.display = _showTw ? '' : 'none';
  });
}

async function onProduksiBlur(row, cell) {
  const komoditasId = parseInt(cell.dataset.kom);
  const field = cell.dataset.field;
  const value = cell.value.trim();
  const f = getFilters();
  const original = _produksiMap[komoditasId] || {};

  if (value === String(original[field] || '')) return;

  const statusCell = document.getElementById(`pstatus-${komoditasId}`);
  if (statusCell) statusCell.innerHTML = '<div class="spinner" style="margin:0 auto"></div>';
  setRowUpdating(row, null);
  updateStatusBar('calculating');

  const body = { [field]: value === '' ? null : (field === 'kuantum' ? parseFloat(value) : value) };

  try {
    const res = await patchProduksi(komoditasId, f.wilayah_kode, f.tahun, f.triwulan, body);
    _produksiMap[komoditasId] = { ...original, [field]: value };
    setRowDone(row, true);
    if (statusCell) statusCell.innerHTML = '<span style="color:var(--success)">✓</span>';
    showToast('Produksi disimpan', 'success', 2000);
    if (res.task_id) {
      updateStatusBar('calculating');
      sse.onTask(res.task_id, (ev) => {
        if (ev.type === 'cascade_done') updateStatusBar('done');
      });
    }
  } catch (e) {
    setRowDone(row, false);
    if (statusCell) statusCell.innerHTML = '<span style="color:var(--danger)">⚠</span>';
    showToast('Gagal: ' + e.message, 'error');
  }
}

async function onTwBlur(kom, inp) {
  const tw = parseInt(inp.dataset.tw);
  const value = inp.value.trim();
  const f = getFilters();

  updateTwTotal(kom.id);

  // Simpan ke triwulan spesifik
  const body = { kuantum: value === '' ? null : parseFloat(value) };

  try {
    const res = await patchProduksi(kom.id, f.wilayah_kode, f.tahun, tw, body);
    showToast(`TW${tw} disimpan`, 'success', 1500);
    // Update data lokal
    if (_produksiMap[kom.id]) {
      _produksiMap[kom.id][`tw${tw}`] = value;
    }
    if (res.task_id) {
      updateStatusBar('calculating');
      sse.onTask(res.task_id, (ev) => {
        if (ev.type === 'cascade_done') updateStatusBar('done');
      });
    }
  } catch (e) {
    showToast(`Gagal simpan TW${tw}: ` + e.message, 'error');
  }
}
