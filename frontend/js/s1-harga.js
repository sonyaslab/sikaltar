/**
 * s1-harga.js — S1.H Input Harga Logic
 *
 * Alur:
 *  1. Load hierarki kategori → komoditas
 *  2. Load data harga untuk filter terpilih
 *  3. Render tabel hierarkis
 *  4. Setiap blur pada input → PATCH ke API → spinner → SSE update → animasi
 */

const TAHUN_DASAR = 2010;
let _hierarki = [];     // pohon kategori
let _hargaMap = {};     // { komoditas_id: rowData }
let _tahunDasar = false;

// ── Inisialisasi ─────────────────────────────────────────────────────────────

window.addEventListener('DOMContentLoaded', async () => {
  sse.connect();

  // Filter setup
  await initWilayahFilter(document.getElementById('filter-wilayah'), reloadData);
  initTahunFilter(document.getElementById('filter-tahun'), reloadData);
  initTriwulanFilter(document.getElementById('filter-triwulan'), reloadData);

  // Buttons
  document.getElementById('btn-refresh').addEventListener('click', reloadData);
  document.getElementById('btn-export').addEventListener('click', exportExcel);

  // Listen cascade events → re-read updated rows
  sse.on('cascade', onCascadeEvent);

  // Keyboard shortcut
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      const focused = document.activeElement;
      if (focused.classList.contains('cell-input')) focused.blur();
    }
  });

  // Load data
  await loadHierarki();
  await reloadData();
});


// ── Data Loading ──────────────────────────────────────────────────────────────

async function loadHierarki() {
  try {
    _hierarki = await getHierarki();
  } catch (e) {
    showToast('Gagal memuat hierarki kategori: ' + e.message, 'error');
  }
}

async function reloadData() {
  const f = getApiParams();
  _tahunDasar = (f.tahun === TAHUN_DASAR);

  // Toggle notice
  const notice = document.getElementById('tahun-dasar-notice');
  notice.style.display = _tahunDasar ? 'inline-flex' : 'none';

  document.getElementById('filter-info').textContent =
    `${getFilters().wilayah_nama} · ${f.tahun}${f.triwulan ? ' · TW'+f.triwulan : ' · Tahunan'}`;

  // Show skeleton
  document.getElementById('harga-tbody').innerHTML =
    `<tr><td colspan="8" class="table-empty-msg"><div class="spinner" style="margin:0 auto"></div></td></tr>`;

  try {
    const [_, hargaList] = await Promise.all([
      _hierarki.length ? null : loadHierarki(),
      getHarga(f.wilayah_kode, f.tahun, f.triwulan),
    ]);
    _hargaMap = {};
    (hargaList || []).forEach(row => { _hargaMap[row.komoditas_id] = row; });

    renderTable();
    document.getElementById('last-update').textContent =
      'Terakhir dimuat: ' + new Date().toLocaleTimeString('id-ID');
  } catch (e) {
    showToast('Gagal memuat data harga: ' + e.message, 'error');
    document.getElementById('harga-tbody').innerHTML =
      `<tr><td colspan="8" class="table-empty-msg"><div class="icon">⚠️</div>Gagal memuat. <button class="btn btn-ghost btn-sm" onclick="reloadData()">Coba lagi</button></td></tr>`;
  }
}


// ── Render Tabel Hierarkis ────────────────────────────────────────────────────

function renderTable() {
  const tbody = document.getElementById('harga-tbody');
  tbody.innerHTML = '';
  let rowNo = 0;

  function renderKategori(node, depth = 0) {
    // Header baris kategori
    const tr = document.createElement('tr');
    if (depth === 0) {
      tr.className = 'row-cat-header';
      tr.innerHTML = `
        <td colspan="8">
          <span class="cat-code">${node.kode}</span>${node.nama}
        </td>`;
    } else if (depth === 1) {
      tr.className = 'row-subcat';
      tr.innerHTML = `
        <td class="col-no"></td>
        <td colspan="7" style="padding-left:${16 + depth*12}px">
          <span class="sub-code">${node.kode}</span>${node.nama}
        </td>`;
    } else {
      tr.className = 'row-subcat-2';
      tr.innerHTML = `
        <td class="col-no"></td>
        <td colspan="7" style="padding-left:${16 + depth*12}px">
          <span class="sub-code">${node.kode}</span>${node.nama}
        </td>`;
    }
    tbody.appendChild(tr);

    // Komoditas dalam kategori ini
    (node.komoditas || []).forEach(kom => {
      rowNo++;
      tbody.appendChild(buildKomoditasRow(kom, rowNo));
    });

    // Sub-kategori (rekursif)
    (node.children || []).forEach(child => renderKategori(child, depth + 1));
  }

  if (!_hierarki || _hierarki.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="table-empty-msg">
      <div class="icon">📋</div>Tidak ada data hierarki.</td></tr>`;
    return;
  }

  _hierarki.forEach(root => renderKategori(root, 0));

  if (rowNo === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="table-empty-msg">
      <div class="icon">🌾</div>Belum ada komoditas terdaftar.</td></tr>`;
  }
}


function buildKomoditasRow(kom, rowNo) {
  const harga = _hargaMap[kom.id] || {};
  const f = getFilters();
  const isTahunDasar = (f.tahun === TAHUN_DASAR);

  const hargaBerlaku = harga.harga_berlaku || '';
  const hargaKonstan = harga.harga_konstan_2010 || '';
  const hasData = hargaBerlaku !== '' || hargaKonstan !== '';

  const tr = document.createElement('tr');
  tr.className = `row-komoditas ${hasData ? 'row-filled' : 'row-empty'}`;
  tr.dataset.komoditasId = kom.id;

  // Harga konstan: editable hanya di tahun 2010
  const hargaKonstanCell = isTahunDasar
    ? `<input type="number" class="cell-input" id="hk-${kom.id}"
         data-field="harga_konstan_2010" data-kom="${kom.id}"
         value="${hargaKonstan}" placeholder="0"
         min="0" step="1000" title="Harga Konstan Tahun Dasar 2010">`
    : `<span class="readonly-badge" title="Nilai tetap dari tahun 2010. Untuk mengubah, pilih tahun 2010.">
         🔒 ${hargaKonstan ? formatRupiah(hargaKonstan) : '≡ Dasar 2010'}
       </span>`;

  tr.innerHTML = `
    <td class="col-no">${rowNo}</td>
    <td>
      <div class="kom-nama">${kom.nama}</div>
      <div class="kom-wujud">${kom.wujud_produksi || ''}</div>
    </td>
    <td>${kom.wujud_produksi || '<span style="color:var(--text-light)">—</span>'}</td>
    <td style="color:var(--text-muted);font-size:0.78rem">${kom.satuan_harga || '—'}</td>
    <td class="num-right">
      <input type="number" class="cell-input" id="hb-${kom.id}"
        data-field="harga_berlaku" data-kom="${kom.id}"
        value="${hargaBerlaku}" placeholder="0"
        min="0" step="1000">
    </td>
    <td class="num-right" id="hk-cell-${kom.id}">
      ${hargaKonstanCell}
    </td>
    <td>
      <select class="cell-select" data-field="sumber_data" data-kom="${kom.id}">
        ${SUMBER_DATA_OPTIONS.map(s =>
          `<option value="${s}" ${harga.sumber_data === s ? 'selected' : ''}>${s || '— Pilih Sumber —'}</option>`
        ).join('')}
      </select>
    </td>
    <td class="col-action" id="status-${kom.id}" style="text-align:center">
      ${hasData ? '<span style="color:var(--success);font-size:1rem">✓</span>' : ''}
    </td>
  `;

  // Event listeners
  const inputs = tr.querySelectorAll('.cell-input');
  inputs.forEach(inp => {
    inp.addEventListener('focus', () => inp.select());
    inp.addEventListener('blur', () => onCellBlur(tr, inp));
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { inp.value = ''; inp.blur(); }
    });
  });

  const select = tr.querySelector('.cell-select[data-field="sumber_data"]');
  if (select) {
    select.addEventListener('change', () => onCellBlur(tr, select));
  }

  return tr;
}


// ── Auto-Save on Blur ─────────────────────────────────────────────────────────

async function onCellBlur(row, cell) {
  const komoditasId = parseInt(cell.dataset.kom);
  const field = cell.dataset.field;
  const value = cell.value.trim();
  const f = getFilters();

  // Skip jika tidak berubah
  const originalData = _hargaMap[komoditasId] || {};
  const originalVal = String(originalData[field] || '');
  if (value === originalVal) return;

  // Tampilkan spinner di kolom status
  const statusCell = document.getElementById(`status-${komoditasId}`);
  if (statusCell) statusCell.innerHTML = '<div class="spinner" style="margin:0 auto"></div>';

  // Set row updating
  setRowUpdating(row, null);
  updateStatusBar('calculating', 'Menyimpan dan menghitung ulang...');

  const body = { [field]: value === '' ? null : (field === 'sumber_data' ? value : parseFloat(value)) };

  try {
    const res = await patchHarga(komoditasId, f.wilayah_kode, f.tahun, f.triwulan, body);

    // Update local map
    _hargaMap[komoditasId] = { ...(originalData), [field]: value };

    // Row success animation
    setRowDone(row, true);
    if (statusCell) statusCell.innerHTML = '<span style="color:var(--success);font-size:1rem">✓</span>';

    showToast(`Data disimpan · Cascade berjalan`, 'success', 2000);

    // Track task untuk cascade update
    if (res.task_id) {
      updateStatusBar('calculating', 'Kalkulasi cascade berjalan...');
      sse.onTask(res.task_id, (ev) => {
        if (ev.type === 'cascade_done') {
          updateStatusBar('done');
          showToast('Kalkulasi selesai ✓', 'success', 1500);
        }
      });
    }
  } catch (e) {
    setRowDone(row, false);
    if (statusCell) statusCell.innerHTML = '<span style="color:var(--danger)">⚠</span>';
    showToast(`Gagal menyimpan: ${e.message}`, 'error');
    updateStatusBar('done');
  }
}


// ── Cascade Event Handler ─────────────────────────────────────────────────────

function onCascadeEvent(ev) {
  if (ev.type === 'cascade_done') {
    updateStatusBar('done');
  }
  // Jika cascade menyertakan data harga baru → update tampilan (opsional)
}


// ── Export ────────────────────────────────────────────────────────────────────

function exportExcel() {
  const f = getFilters();
  showToast('Export Excel akan segera tersedia di versi berikutnya.', 'warn', 3000);
}
