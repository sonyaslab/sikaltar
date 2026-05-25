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
  document.getElementById('filter-info').textContent =
    `${f.wilayah_nama} · ${f.tahun} · Rasio ${_currentJenis} · Berlaku: ${berlaku}`;
  document.getElementById('rasio-tbody').innerHTML =
    `<tr><td colspan="7" class="table-empty-msg"><div class="spinner" style="margin:0 auto"></div></td></tr>`;

  try {
    _rasioData = await getRasio(_currentJenis, f.tahun, berlaku, f.wilayah_kode);
    renderTable();
    document.getElementById('last-update').textContent =
      'Dimuat: ' + new Date().toLocaleTimeString('id-ID');
  } catch (e) {
    showToast('Gagal memuat: ' + e.message, 'error');
    document.getElementById('rasio-tbody').innerHTML =
      `<tr><td colspan="7" class="table-empty-msg"><div class="icon">⚠️</div>Gagal memuat data rasio.</td></tr>`;
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
