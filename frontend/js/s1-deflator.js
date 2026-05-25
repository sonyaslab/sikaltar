/**
 * s1-deflator.js — S1.I Indeks Deflator Logic
 *
 * Hanya kategori dengan metode_adhk='Deflasi' yang bisa diisi.
 * Kolom "Tahun Lalu" dan "Perubahan (%)" = READ-ONLY.
 */

let _deflatorData = [];

window.addEventListener('DOMContentLoaded', async () => {
  sse.connect();

  await initWilayahFilter(document.getElementById('filter-wilayah'), reloadData);
  initTahunFilter(document.getElementById('filter-tahun'), reloadData);
  initTriwulanFilter(document.getElementById('filter-triwulan'), reloadData);
  document.getElementById('btn-refresh').addEventListener('click', reloadData);

  sse.on('cascade', (ev) => {
    if (ev.type === 'cascade_done') updateStatusBar('done');
  });

  await reloadData();
});

async function reloadData() {
  const f = getApiParams();
  document.getElementById('filter-info').textContent =
    `${getFilters().wilayah_nama} · ${f.tahun}${f.triwulan ? ' · TW'+f.triwulan : ' · Tahunan'}`;
  document.getElementById('deflator-tbody').innerHTML =
    `<tr><td colspan="8" class="table-empty-msg"><div class="spinner" style="margin:0 auto"></div></td></tr>`;

  try {
    _deflatorData = await getDeflator(f.wilayah_kode, f.tahun, f.triwulan);
    renderTable();
    document.getElementById('last-update').textContent =
      'Dimuat: ' + new Date().toLocaleTimeString('id-ID');
  } catch (e) {
    showToast('Gagal memuat deflator: ' + e.message, 'error');
    document.getElementById('deflator-tbody').innerHTML =
      `<tr><td colspan="8" class="table-empty-msg"><div class="icon">⚠️</div>Gagal memuat.</td></tr>`;
  }
}

function renderTable() {
  const tbody = document.getElementById('deflator-tbody');
  tbody.innerHTML = '';
  let rowNo = 0;

  _deflatorData.forEach(row => {
    rowNo++;
    const tr = buildDeflatorRow(row, rowNo);
    tbody.appendChild(tr);
  });

  if (rowNo === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="table-empty-msg">
      <div class="icon">📉</div>Tidak ada data deflator.</td></tr>`;
  }
}

function buildDeflatorRow(row, rowNo) {
  const tr = document.createElement('tr');
  const isEditable = row.is_editable;
  const hasValue = row.nilai_indeks !== null && row.nilai_indeks !== undefined;

  tr.className = isEditable
    ? `row-komoditas row-deflator-editable ${hasValue ? 'row-filled' : 'row-empty'}`
    : 'row-komoditas row-deflator-disabled';
  tr.dataset.kode = row.kategori_kode;

  // Format perubahan %
  let perubahanHtml = '<span style="color:var(--text-light)">—</span>';
  if (row.perubahan_pct !== null && row.perubahan_pct !== undefined) {
    const pct = parseFloat(row.perubahan_pct);
    const cls = pct >= 0 ? 'color:var(--success)' : 'color:var(--danger)';
    const sign = pct >= 0 ? '+' : '';
    perubahanHtml = `<span style="${cls};font-family:var(--font-mono);font-weight:600">
      ${sign}${pct.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}%
    </span>`;
  }

  // Metode badge
  const metodeBadge = (met) => {
    if (!met) return '<span style="color:var(--text-light)">—</span>';
    const colors = {
      'Produksi': 'badge-blue',
      'Revaluasi': 'badge-green',
      'Deflasi': 'badge-yellow',
    };
    return `<span class="badge ${colors[met] || 'badge-gray'}">${met}</span>`;
  };

  tr.innerHTML = `
    <td class="col-no">${rowNo}</td>
    <td>
      <span class="sub-code" style="font-size:0.73rem;color:var(--text-muted);font-family:var(--font-mono);margin-right:6px">${row.kategori_kode}</span>
      <span style="font-size:0.83rem${isEditable ? '' : ';color:var(--text-muted)'}">
        ${row.kategori_nama}
        ${!isEditable ? '<span style="font-size:0.72rem;color:var(--text-light);margin-left:6px">(tidak menggunakan deflator)</span>' : ''}
      </span>
    </td>
    <td>${metodeBadge(row.metode_adhb)}</td>
    <td>${metodeBadge(row.metode_adhk)}</td>
    <td class="num-right">
      ${isEditable
        ? `<input type="number" class="cell-input" id="deflator-${row.kategori_kode.replace(/\./g,'_')}"
            data-kode="${row.kategori_kode}"
            value="${hasValue ? row.nilai_indeks : ''}"
            placeholder="100.0000" step="0.0001" min="0" max="10000"
            title="Masukkan indeks deflator (basis 2010=100)">`
        : `<span class="readonly-badge">Otomatis</span>`}
    </td>
    <td class="num-right">
      <span style="font-family:var(--font-mono);color:var(--text-muted);font-size:0.82rem">
        ${row.nilai_indeks_tahun_lalu
          ? parseFloat(row.nilai_indeks_tahun_lalu).toLocaleString('id-ID', { minimumFractionDigits: 4 })
          : '—'}
      </span>
    </td>
    <td class="num-right">${perubahanHtml}</td>
    <td class="col-action" style="text-align:center" id="dstatus-${row.kategori_kode.replace(/\./g,'_')}">
      ${isEditable
        ? (hasValue ? '<span style="color:var(--success)">✓</span>' : '')
        : '<span style="color:var(--text-light);font-size:0.8rem">N/A</span>'}
    </td>
  `;

  // Events
  if (isEditable) {
    const inp = tr.querySelector('.cell-input');
    inp.addEventListener('focus', () => inp.select());
    inp.addEventListener('blur', () => onDeflatorBlur(tr, inp));
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { inp.value = ''; inp.blur(); }
    });
  }

  return tr;
}

async function onDeflatorBlur(row, inp) {
  const kode = inp.dataset.kode;
  const value = inp.value.trim();
  const f = getFilters();

  // Validasi tahun dasar — 2010 harus = 100
  if (f.tahun === 2010 && value && parseFloat(value) !== 100) {
    showToast('⚠ Pada tahun dasar 2010, indeks harus bernilai 100.0000', 'warn', 4000);
    inp.value = '100';
    return;
  }

  if (!value) return;

  const statusKey = kode.replace(/\./g, '_');
  const statusCell = document.getElementById(`dstatus-${statusKey}`);
  if (statusCell) statusCell.innerHTML = '<div class="spinner" style="margin:0 auto"></div>';
  setRowUpdating(row, null);
  updateStatusBar('calculating');

  try {
    const res = await patchDeflator(kode, f.wilayah_kode, f.tahun, f.triwulan, { nilai_indeks: parseFloat(value) });
    setRowDone(row, true);
    if (statusCell) statusCell.innerHTML = '<span style="color:var(--success)">✓</span>';
    showToast(`Deflator ${kode} disimpan ✓`, 'success', 2000);
    if (res.task_id) {
      updateStatusBar('calculating', 'Kalkulasi ADHK berjalan...');
      sse.onTask(res.task_id, (ev) => {
        if (ev.type === 'cascade_done') {
          updateStatusBar('done');
          // Refresh perubahan% di baris ini setelah cascade
          setTimeout(reloadData, 500);
        }
      });
    }
  } catch (e) {
    setRowDone(row, false);
    if (statusCell) statusCell.innerHTML = '<span style="color:var(--danger)">⚠</span>';
    showToast('Gagal: ' + e.message, 'error');
    updateStatusBar('done');
  }
}
