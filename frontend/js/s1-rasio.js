/**
 * s1-rasio.js — S1.R Rasio Logic
 *
 * Fitur:
 *  - 4 tab: OS / WIP / KA / ADJ
 *  - Kolom default (read-only) vs override lokal (editable)
 *  - Impact preview modal sebelum save
 *  - Reset per baris (hapus override)
 *  - Cascade trigger setelah save
 */

let _currentJenis = 'OS';
let _rasioData = [];
let _pendingOverride = null;   // Data yang menunggu konfirmasi modal
let _adjDataAdhb = [];         // Data ADJ ADHB (khusus tab ADJ)
let _adjDataAdhk = [];         // Data ADJ ADHK (khusus tab ADJ)

window.addEventListener('DOMContentLoaded', async () => {
  sse.connect();

  await initWilayahFilter(document.getElementById('filter-wilayah'), reloadData);
  initTahunFilter(document.getElementById('filter-tahun'), reloadData);

  document.getElementById('filter-berlaku').addEventListener('change', reloadData);
  document.getElementById('btn-refresh').addEventListener('click', reloadData);

  // Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      _currentJenis = btn.dataset.jenis;
      reloadData();
    });
  });

  // Modal
  document.getElementById('modal-cancel').addEventListener('click', closeModal);
  document.getElementById('modal-confirm').addEventListener('click', confirmOverride);
  document.getElementById('impact-modal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeModal();
  });

  sse.on('cascade', (ev) => {
    if (ev.type === 'cascade_done') {
      updateStatusBar('done');
      showToast('Kalkulasi ulang selesai ✓', 'success', 2000);
    }
  });

  await reloadData();
});

async function reloadData() {
  const f = getFilters();
  const berlaku = document.getElementById('filter-berlaku').value;
  const isAdj = _currentJenis === 'ADJ';

  // Toggle filter berlaku (tidak relevan untuk ADJ — tampil keduanya sekaligus)
  const berlakuWrap = document.getElementById('berlaku-filter-wrap');
  if (berlakuWrap) berlakuWrap.style.display = isAdj ? 'none' : 'contents';

  document.getElementById('filter-info').textContent =
    isAdj
      ? `${f.wilayah_nama} · ${f.tahun} · Rasio ADJ (ADHB & ADHK)`
      : `${f.wilayah_nama} · ${f.tahun} · Rasio ${_currentJenis} · Berlaku: ${berlaku}`;

  const colCount = isAdj ? 6 : 7;
  document.getElementById('rasio-tbody').innerHTML =
    `<tr><td colspan="${colCount}" class="table-empty-msg"><div class="spinner" style="margin:0 auto"></div></td></tr>`;

  // Update header kolom
  updateTableHeader(isAdj);

  try {
    if (isAdj) {
      [_adjDataAdhb, _adjDataAdhk] = await Promise.all([
        getRasio('ADJ', f.tahun, 'ADHB', f.wilayah_kode),
        getRasio('ADJ', f.tahun, 'ADHK', f.wilayah_kode),
      ]);
      renderAdjTable();
    } else {
      _rasioData = await getRasio(_currentJenis, f.tahun, berlaku, f.wilayah_kode);
      renderTable();
    }
    document.getElementById('last-update').textContent =
      'Dimuat: ' + new Date().toLocaleTimeString('id-ID');
  } catch (e) {
    showToast('Gagal memuat: ' + e.message, 'error');
    document.getElementById('rasio-tbody').innerHTML =
      `<tr><td colspan="${colCount}" class="table-empty-msg"><div class="icon">⚠️</div>Gagal memuat data rasio.</td></tr>`;
  }
}

function renderTable() {
  const tbody = document.getElementById('rasio-tbody');
  tbody.innerHTML = '';
  let rowNo = 0;

  if (!_rasioData || _rasioData.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="table-empty-msg">
      <div class="icon">📊</div>Tidak ada data rasio.</td></tr>`;
    return;
  }

  // Group by level for visual hierarchy
  _rasioData.forEach(row => {
    rowNo++;
    const tr = buildRasioRow(row, rowNo);
    tbody.appendChild(tr);
  });
}

// ── Header Kolom Dinamis ─────────────────────────────────────────────────────

function updateTableHeader(isAdj) {
  const theadRow = document.getElementById('rasio-thead-row');
  if (!theadRow) return;
  if (isAdj) {
    theadRow.innerHTML = `
      <th class="col-no">No</th>
      <th style="min-width:240px">Subkategori</th>
      <th class="col-nilai" style="min-width:160px">ADJ ADHB <small>(%)</small></th>
      <th class="col-nilai" style="min-width:160px">ADJ ADHK <small>(%)</small></th>
      <th style="width:100px;text-align:center">Tahun Berlaku</th>
      <th class="col-action">Aksi</th>
    `;
  } else {
    theadRow.innerHTML = `
      <th class="col-no">No</th>
      <th style="min-width:280px">Kategori</th>
      <th class="col-nilai">Nilai Default BPS</th>
      <th class="col-nilai">Override Lokal</th>
      <th style="width:80px">Status</th>
      <th style="width:160px">Keterangan</th>
      <th class="col-action">Aksi</th>
    `;
  }
}

// ── ADJ Table (khusus: persen, ADHB & ADHK berdampingan) ────────────────────

function renderAdjTable() {
  const tbody = document.getElementById('rasio-tbody');
  tbody.innerHTML = '';

  // Buat map ADHB by kategori_kode untuk merge dengan ADHK
  const adhbMap = {};
  _adjDataAdhb.forEach(r => { adhbMap[r.kategori_kode] = r; });

  let rowNo = 0;
  _adjDataAdhk.forEach(rowK => {
    const rowB = adhbMap[rowK.kategori_kode] || {};
    rowNo++;
    tbody.appendChild(buildAdjRow(rowB, rowK, rowNo));
  });

  if (rowNo === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="table-empty-msg">
      <div class="icon">📊</div>Tidak ada data ADJ.</td></tr>`;
  }
}

function buildAdjRow(rowB, rowK, rowNo) {
  const f = getFilters();
  const tr = document.createElement('tr');

  // Visual level
  if (rowK.level === 2) tr.className = 'row-subcat';
  else if (rowK.level >= 3) tr.className = 'row-subcat-2';

  const defB = rowB.nilai_default !== null && rowB.nilai_default !== undefined ? parseFloat(rowB.nilai_default) : null;
  const defK = rowK.nilai_default !== null && rowK.nilai_default !== undefined ? parseFloat(rowK.nilai_default) : null;
  const ovB  = rowB.nilai_override !== null && rowB.nilai_override !== undefined ? parseFloat(rowB.nilai_override) : null;
  const ovK  = rowK.nilai_override !== null && rowK.nilai_override !== undefined ? parseFloat(rowK.nilai_override) : null;

  // Helper: tampil nilai desimal sebagai persen
  const toPct = (v) => v !== null ? (v * 100).toFixed(4) : '';
  const showDef = (v) => v !== null
    ? `<div style="font-size:0.73rem;color:var(--text-muted);margin-bottom:3px">Default: <strong>${(v*100).toFixed(2)}%</strong></div>`
    : '';

  const isOvB = rowB.is_overridden;
  const isOvK = rowK.is_overridden;
  const hasAnyOverride = isOvB || isOvK;
  const kodeId = rowK.kategori_kode.replace(/\./g, '_');

  const adjInputCell = (berlaku, defVal, ovVal, isOv, ovId) => `
    <div style="display:flex;flex-direction:column;gap:2px">
      ${showDef(defVal)}
      <div style="display:flex;align-items:center;gap:4px;justify-content:flex-end">
        <input type="number" class="override-input ${isOv ? 'has-override' : ''}"
          id="adj-${berlaku.toLowerCase()}-${kodeId}"
          data-kode="${rowK.kategori_kode}" data-berlaku="${berlaku}"
          data-override-id="${ovId || ''}"
          value="${toPct(ovVal)}"
          placeholder="${defVal !== null ? (defVal*100).toFixed(2) : '0.00'}"
          step="0.01" min="0" max="100"
          title="${isOv ? 'Override lokal (%)' : 'Input dalam persen, mis: 10.12 untuk 10,12%'}"
          style="width:85px">
        <span style="font-size:0.75rem;color:var(--text-muted)">%</span>
        <span style="font-size:0.8rem" title="${isOv ? 'Override lokal aktif' : 'Menggunakan default BPS'}">${isOv ? '✏️' : '🔒'}</span>
      </div>
    </div>`;

  tr.innerHTML = `
    <td class="col-no" style="color:var(--text-light);font-size:0.73rem">${rowNo}</td>
    <td>
      <span class="sub-code">${rowK.kategori_kode}</span>
      <span class="kom-nama">${rowK.kategori_nama}</span>
    </td>
    <td class="num-right">${adjInputCell('ADHB', defB, ovB, isOvB, rowB.override_id)}</td>
    <td class="num-right">${adjInputCell('ADHK', defK, ovK, isOvK, rowK.override_id)}</td>
    <td style="text-align:center;font-size:0.83rem;color:var(--text-muted);font-family:var(--font-mono)">${f.tahun}</td>
    <td class="col-action" style="text-align:center">
      ${hasAnyOverride
        ? `<button class="btn-reset-override"
             onclick="resetAdjOverride('${rowB.override_id || ''}','${rowK.override_id || ''}','${rowK.kategori_kode}')"
             title="Reset ADHB &amp; ADHK ke default BPS">↺ Reset</button>`
        : ''}
    </td>
  `;

  // Events — show impact preview on change, use modal reuse
  ['ADHB', 'ADHK'].forEach(berlaku => {
    const inp = tr.querySelector(`#adj-${berlaku.toLowerCase()}-${kodeId}`);
    if (inp) {
      inp.addEventListener('focus', () => inp.select());
      inp.addEventListener('change', () => showAdjImpactPreview(rowK.kategori_kode, inp, berlaku));
    }
  });

  return tr;
}

async function showAdjImpactPreview(kategoriKode, inputEl, berlakuUntuk) {
  const nilaiPersen = parseFloat(inputEl.value);
  if (isNaN(nilaiPersen) || nilaiPersen < 0) return;

  const nilaiDesimal = nilaiPersen / 100;
  const f = getFilters();

  document.getElementById('impact-modal-content').innerHTML =
    `<div class="spinner" style="margin:0 auto;display:block"></div>`;
  document.getElementById('impact-modal').style.display = 'flex';

  try {
    const preview = await getRasioImpactPreview({
      kategori_kode: kategoriKode,
      jenis_rasio: 'ADJ',
      tahun: f.tahun,
      berlaku_untuk: berlakuUntuk,
      nilai_baru: nilaiDesimal,
      wilayah_kode: f.wilayah_kode,
    });

    const fmtDelta = (v) => {
      if (!v) return '<span style="color:var(--text-muted)">—</span>';
      const n = parseFloat(v);
      const cls = n >= 0 ? 'impact-delta-pos' : 'impact-delta-neg';
      const sign = n >= 0 ? '+' : '';
      return `<span class="${cls}">${sign}${Math.abs(n).toLocaleString('id-ID', {maximumFractionDigits:0})} Juta</span>`;
    };

    document.getElementById('impact-modal-content').innerHTML = `
      <p style="font-size:0.83rem;color:var(--text-muted);margin-bottom:8px">
        Mengubah rasio <strong>ADJ ${berlakuUntuk}</strong> kategori <strong>${kategoriKode}</strong><br>
        dari <strong>${preview.nilai_lama ? (parseFloat(preview.nilai_lama)*100).toFixed(2)+'%' : '—'}</strong>
        menjadi <strong>${nilaiPersen.toFixed(2)}%</strong>
        <small style="color:var(--text-light)">(= ${nilaiDesimal.toFixed(4)} desimal)</small>
      </p>
      <div class="impact-card">
        <div class="impact-row"><span class="label">Komoditas terdampak</span><span class="value">${preview.komoditas_count} komoditas</span></div>
        <div class="impact-row"><span class="label">NTB Sebelum</span><span class="value">${preview.ntb_adhb_sebelum ? formatRupiah(parseFloat(preview.ntb_adhb_sebelum),0)+' Juta' : '—'}</span></div>
        <div class="impact-row"><span class="label">Perubahan NTB ADHB</span><span class="value">${fmtDelta(preview.ntb_adhb_delta)}</span></div>
        <div class="impact-row"><span class="label">Perubahan NTB ADHK</span><span class="value">${fmtDelta(preview.ntb_adhk_delta)}</span></div>
      </div>
      <p style="font-size:0.75rem;color:var(--text-muted);margin-top:8px">
        ⚠ Estimasi indikatif. Nilai akhir dihitung ulang setelah disimpan.
      </p>`;

    _pendingOverride = {
      kategori_kode: kategoriKode,
      jenis_rasio: 'ADJ',
      wilayah_kode: f.wilayah_kode,
      tahun: f.tahun,
      nilai: nilaiDesimal,
      berlaku_untuk: berlakuUntuk,
      keterangan: null,
    };
  } catch (e) {
    document.getElementById('impact-modal-content').innerHTML =
      `<p class="badge badge-red">⚠ Gagal memuat estimasi: ${e.message}</p>
       <p style="font-size:0.8rem;margin-top:8px">Klik Simpan untuk tetap melanjutkan tanpa preview.</p>`;
    _pendingOverride = {
      kategori_kode: kategoriKode,
      jenis_rasio: 'ADJ',
      wilayah_kode: f.wilayah_kode,
      tahun: f.tahun,
      nilai: nilaiDesimal,
      berlaku_untuk: berlakuUntuk,
      keterangan: null,
    };
  }
}

async function resetAdjOverride(overrideIdB, overrideIdK, kategoriKode) {
  if (!confirm(`Reset ADJ ${kategoriKode} (ADHB & ADHK) ke nilai default BPS?\nPerubahan ini akan mentrigger kalkulasi ulang.`)) return;

  updateStatusBar('calculating');
  const toDelete = [overrideIdB, overrideIdK].filter(id => id && id !== '');

  try {
    await Promise.all(toDelete.map(id => deleteRasioOverride(id)));
    showToast(`ADJ ${kategoriKode} direset ke default BPS.`, 'success', 2500);
    await reloadData();
    updateStatusBar('done');
  } catch (e) {
    showToast('Gagal reset: ' + e.message, 'error');
    updateStatusBar('done');
  }
}

function buildRasioRow(row, rowNo) {
  const tr = document.createElement('tr');
  const isOverridden = row.is_overridden;
  const defaultVal = row.nilai_default !== null ? parseFloat(row.nilai_default) : null;
  const overrideVal = row.nilai_override !== null ? parseFloat(row.nilai_override) : null;
  const displayVal = isOverridden ? overrideVal : defaultVal;
  const pct = displayVal !== null
    ? `(${(displayVal * 100).toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}%)`
    : '';

  // Row style by level
  if (row.level === 2) {
    tr.className = 'row-subcat';
  } else if (row.level >= 3) {
    tr.className = 'row-subcat-2';
  }

  const statusIcon = isOverridden ? '✏️' : (defaultVal !== null ? '🔒' : '⚠️');
  const statusTitle = isOverridden
    ? 'Menggunakan override lokal'
    : (defaultVal !== null ? 'Menggunakan nilai default BPS' : 'Nilai tidak tersedia');

  tr.innerHTML = `
    <td class="col-no" style="color:var(--text-light);font-size:0.73rem">${rowNo}</td>
    <td>
      <span class="sub-code">${row.kategori_kode}</span>
      <span class="kom-nama" style="cursor:pointer" title="Klik untuk estimasi dampak" 
            onclick="showImpactPreview('${row.kategori_kode}', document.getElementById('override-${row.kategori_kode.replace(/\./g,'_')}'))">
        ${row.kategori_nama}
      </span>
    </td>
    <td class="num-right">
      ${defaultVal !== null
        ? `<span class="rasio-default">${defaultVal.toLocaleString('id-ID', { minimumFractionDigits: 4 })} <span class="pct-display">(${(defaultVal*100).toFixed(2)}%)</span></span>`
        : '<span style="color:var(--text-light)">—</span>'}
    </td>
    <td class="num-right">
      <div style="display:flex;align-items:center;gap:6px;justify-content:flex-end">
        <input type="number" class="override-input ${isOverridden ? 'has-override' : ''}"
          id="override-${row.kategori_kode.replace(/\./g,'_')}"
          data-kode="${row.kategori_kode}"
          data-override-id="${row.override_id || ''}"
          value="${overrideVal !== null ? overrideVal : ''}"
          placeholder="${defaultVal !== null ? defaultVal.toFixed(4) : '0.0000'}"
          step="0.0001" min="0" max="10"
          title="${statusTitle}">
        ${isOverridden ? `<span class="pct-display">(${(overrideVal*100).toFixed(2)}%)</span>` : ''}
      </div>
    </td>
    <td style="text-align:center" title="${statusTitle}">
      ${statusIcon}
    </td>
    <td>
      <input type="text" class="cell-input" style="font-size:0.78rem"
        id="ket-${row.kategori_kode.replace(/\./g,'_')}"
        data-kode="${row.kategori_kode}"
        value="${row.override_keterangan || ''}"
        placeholder="${isOverridden ? 'Catatan...' : ''}">
    </td>
    <td class="col-action" style="text-align:center">
      ${isOverridden
        ? `<button class="btn-reset-override" onclick="resetOverride('${row.override_id}', '${row.kategori_kode}')" title="Reset ke nilai default BPS">
             ↺ Reset
           </button>`
        : ''}
    </td>
  `;

  // Events on override input
  const overrideInp = tr.querySelector('.override-input');
  overrideInp.addEventListener('change', () => {
    showImpactPreview(row.kategori_kode, overrideInp);
  });
  overrideInp.addEventListener('focus', () => overrideInp.select());

  return tr;
}

// ── Impact Preview Modal ───────────────────────────────────────────────────────

async function showImpactPreview(kategoriKode, inputEl) {
  const nilaiInput = parseFloat(inputEl.value);
  if (isNaN(nilaiInput)) return;

  const f = getFilters();
  const berlaku = document.getElementById('filter-berlaku').value;
  const keterangan = document.getElementById(`ket-${kategoriKode.replace(/\./g,'_')}`)?.value || '';

  // Tampilkan modal dengan loading
  document.getElementById('impact-modal-content').innerHTML =
    `<div class="spinner" style="margin:0 auto;display:block"></div>`;
  document.getElementById('impact-modal').style.display = 'flex';

  try {
    const preview = await getRasioImpactPreview({
      kategori_kode: kategoriKode,
      jenis_rasio: _currentJenis,
      tahun: f.tahun,
      berlaku_untuk: berlaku,
      nilai_baru: nilaiInput,
      wilayah_kode: f.wilayah_kode,
    });

    const fmtDelta = (v) => {
      if (v === null) return '<span style="color:var(--text-muted)">—</span>';
      const n = parseFloat(v);
      const cls = n >= 0 ? 'impact-delta-pos' : 'impact-delta-neg';
      const sign = n >= 0 ? '+' : '';
      return `<span class="${cls}">${sign}${Math.abs(n).toLocaleString('id-ID', {maximumFractionDigits:0})} Juta</span>`;
    };

    document.getElementById('impact-modal-content').innerHTML = `
      <p style="font-size:0.83rem;color:var(--text-muted);margin-bottom:8px">
        Mengubah rasio <strong>${_currentJenis}</strong> kategori <strong>${kategoriKode}</strong>
        dari <strong>${preview.nilai_lama ? (parseFloat(preview.nilai_lama)*100).toFixed(2)+'%' : '—'}</strong>
        menjadi <strong>${(nilaiInput*100).toFixed(2)}%</strong>
      </p>
      <div class="impact-card">
        <div class="impact-row"><span class="label">Komoditas terdampak</span><span class="value">${preview.komoditas_count} komoditas</span></div>
        <div class="impact-row"><span class="label">NTB ADHB Sebelum</span><span class="value">${preview.ntb_adhb_sebelum ? formatRupiah(parseFloat(preview.ntb_adhb_sebelum),0)+' Juta' : '—'}</span></div>
        <div class="impact-row"><span class="label">NTB ADHB Sesudah</span><span class="value">${preview.ntb_adhb_sesudah ? formatRupiah(parseFloat(preview.ntb_adhb_sesudah),0)+' Juta' : '—'}</span></div>
        <div class="impact-row"><span class="label">Perubahan NTB ADHB</span><span class="value">${fmtDelta(preview.ntb_adhb_delta)}</span></div>
        <div class="impact-row" style="margin-top:6px;border-top:1px solid var(--border);padding-top:6px">
          <span class="label">NTB ADHK Sebelum</span><span class="value">${preview.ntb_adhk_sebelum ? formatRupiah(parseFloat(preview.ntb_adhk_sebelum),0)+' Juta' : '—'}</span>
        </div>
        <div class="impact-row"><span class="label">Perubahan NTB ADHK</span><span class="value">${fmtDelta(preview.ntb_adhk_delta)}</span></div>
      </div>
      <p style="font-size:0.75rem;color:var(--text-muted);margin-top:8px">
        ⚠ Estimasi ini bersifat indikatif. Nilai akhir akan dihitung ulang setelah disimpan.
      </p>`;

    // Simpan pending override untuk tombol Konfirmasi
    _pendingOverride = {
      kategori_kode: kategoriKode,
      jenis_rasio: _currentJenis,
      wilayah_kode: f.wilayah_kode,
      tahun: f.tahun,
      nilai: nilaiInput,
      berlaku_untuk: berlaku,
      keterangan: keterangan || null,
    };

  } catch (e) {
    document.getElementById('impact-modal-content').innerHTML =
      `<p class="badge badge-red">⚠ Gagal memuat estimasi: ${e.message}</p>`;
    _pendingOverride = {
      kategori_kode: kategoriKode,
      jenis_rasio: _currentJenis,
      wilayah_kode: f.wilayah_kode,
      tahun: f.tahun,
      nilai: nilaiInput,
      berlaku_untuk: berlaku,
      keterangan: keterangan || null,
    };
  }
}

function closeModal() {
  document.getElementById('impact-modal').style.display = 'none';
  _pendingOverride = null;
}

async function confirmOverride() {
  if (!_pendingOverride) { closeModal(); return; }
  closeModal();

  updateStatusBar('calculating', 'Menyimpan override dan menghitung ulang...');
  try {
    const res = await postRasioOverride(_pendingOverride);
    showToast('Override disimpan. Cascade berjalan...', 'success', 2500);
    if (res.task_id) {
      sse.onTask(res.task_id, (ev) => {
        if (ev.type === 'cascade_done') {
          updateStatusBar('done');
          reloadData();
        }
      });
    }
    await reloadData();
  } catch (e) {
    showToast('Gagal simpan override: ' + e.message, 'error');
    updateStatusBar('done');
  }
}

async function resetOverride(overrideId, kategoriKode) {
  if (!confirm(`Reset rasio ${kategoriKode} ke nilai default BPS?\nPerubahan ini akan mentrigger kalkulasi ulang.`)) return;

  updateStatusBar('calculating');
  try {
    const res = await deleteRasioOverride(overrideId);
    showToast('Override dihapus. Menggunakan default BPS.', 'success', 2500);
    if (res.task_id) {
      sse.onTask(res.task_id, () => updateStatusBar('done'));
    }
    await reloadData();
  } catch (e) {
    showToast('Gagal reset: ' + e.message, 'error');
    updateStatusBar('done');
  }
}
