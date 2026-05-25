/**
 * s2-worksheet.js — Core Worksheet Renderer for S2
 *
 * Fungsi utama:
 *  renderWorksheet(data, mode) → render tabel ADHB + ADHK format BPS
 *  renderRekap(data)           → render tabel rekap subkategori
 *  renderCompare(data)         → render tabel perbandingan side-by-side
 *  updateRows(updates)         → update targeted rows saat SSE push
 */

'use strict';

const WS_MODE = { BOTH: 'both', ADHB: 'adhb', ADHK: 'adhk', COMPARE: 'compare' };
let _currentMode = WS_MODE.BOTH;
let _currentData = null;   // cached worksheet data for SSE updates

// ── Entrypoint ────────────────────────────────────────────────────────────────

function renderWorksheetView(data, mode = WS_MODE.BOTH) {
  _currentData = data;
  _currentMode = mode;
  const container = document.getElementById('ws-container');
  if (!container) return;
  container.innerHTML = '';

  if (!data || !data.rows || data.rows.length === 0) {
    container.innerHTML = `<div class="lk-empty">
      <div class="icon">📋</div>
      <h3>Belum Ada Data</h3>
      <p>Pilih kategori dari sidebar, lalu isi data produksi &amp; harga di S1 terlebih dahulu.</p>
    </div>`;
    return;
  }

  if (mode === WS_MODE.ADHB || mode === WS_MODE.BOTH) {
    container.appendChild(buildSectionSep('ADHB', data));
    container.appendChild(buildWorksheetTable(data, 'adhb'));
  }
  if (mode === WS_MODE.ADHK || mode === WS_MODE.BOTH) {
    container.appendChild(buildSectionSep('ADHK', data));
    container.appendChild(buildWorksheetTable(data, 'adhk'));
  }
  if (mode === WS_MODE.COMPARE) {
    container.innerHTML = '';
    container.appendChild(buildSectionSep('COMPARE', data));
    container.appendChild(buildCompareTable(data));
  }
}

function renderRekapSection(rekapData) {
  const container = document.getElementById('rekap-container');
  if (!container) return;
  container.innerHTML = '';
  if (!rekapData || !rekapData.rows || rekapData.rows.length === 0) return;
  container.appendChild(buildRekapTable(rekapData));
}


// ── Section Separator ─────────────────────────────────────────────────────────

function buildSectionSep(type, data) {
  const div = document.createElement('div');
  div.className = `section-sep${type === 'ADHK' ? ' adhk' : type === 'COMPARE' ? ' adhk' : ''}`;

  const periodeStr = data.triwulan ? `Triwulan ${['I','II','III','IV'][data.triwulan-1]}` : 'Tahunan';
  const labels = {
    'ADHB':    `📊 ATAS DASAR HARGA BERLAKU — ${data.tahun} · ${periodeStr}`,
    'ADHK':    `📉 ATAS DASAR HARGA KONSTAN 2010 — ${data.tahun} · ${periodeStr}`,
    'COMPARE': `🔀 PERBANDINGAN ADHB vs ADHK — ${data.tahun} · ${periodeStr}`,
  };
  div.textContent = labels[type] || type;
  return div;
}


// ── Main Worksheet Table ──────────────────────────────────────────────────────

function buildWorksheetTable(data, basis) {
  const wrap = document.createElement('div');
  wrap.style.cssText = 'overflow-x:auto;border:1px solid var(--border);border-top:none;background:var(--surface);border-radius:0 0 var(--radius) var(--radius);margin-bottom:12px';

  const isB = basis === 'adhb';
  const table = document.createElement('table');
  table.className = 'lk-worksheet-table';
  table.id = `ws-table-${basis}`;

  // ── Header ────────────────────────────────────────────────────────
  table.appendChild(buildTableHeader(basis));

  // ── Body rows ────────────────────────────────────────────────────
  const tbody = document.createElement('tbody');
  let rowNo = 0;
  data.rows.forEach(row => {
    rowNo++;
    tbody.appendChild(buildKomoditasRow(row, rowNo, basis));
  });

  // ── Subtotal rows ────────────────────────────────────────────────
  const st = data.subtotal;
  if (st) {
    tbody.appendChild(buildSubtotalRow('Sub Jumlah Primer', {
      primer: isB ? st.output_primer_adhb : st.output_primer_adhk,
    }));
    tbody.appendChild(buildSubtotalRow('Output Sekunder', {
      sekunder: isB ? st.output_sekunder_adhb : st.output_sekunder_adhk,
    }, 'lk-row-sekunder'));
    if ((isB ? st.output_lainnya_adhb : st.output_lainnya_adhk)) {
      tbody.appendChild(buildSubtotalRow('WIP + Adjustment', {
        lainnya: isB ? st.output_lainnya_adhb : st.output_lainnya_adhk,
      }, 'lk-row-adj'));
    }
    tbody.appendChild(buildTotalRow(st, basis));
  }

  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}


// ── Table Header (2-row) ──────────────────────────────────────────────────────

function buildTableHeader(basis) {
  const thead = document.createElement('thead');
  const isB = basis === 'adhb';

  // Row 1: main groups
  const r1 = document.createElement('tr');
  r1.className = 'header-main';
  const cols1 = [
    { label: 'No',               span: 1, rowspan: 2, class: 'col-sticky col-no' },
    { label: 'Komoditas',        span: 1, rowspan: 2, class: 'col-sticky col-kom' },
    { label: 'Wujud',            span: 1, rowspan: 2 },
    { label: 'Satuan',           span: 1, rowspan: 2 },
    { label: 'Kuantum',          span: 1, rowspan: 2 },
    { label: isB ? 'Harga Berlaku (Rp)' : 'Harga Konstan 2010 (Rp)', span: 1, rowspan: 2 },
    { label: 'Output Utama (Juta Rp)',   span: 1, rowspan: 2 },
    { label: 'Output Ikutan',    span: 2 },
    { label: 'WIP/CBR',          span: 2 },
    { label: 'Total Primer (Juta Rp)',   span: 1, rowspan: 2 },
    { label: 'Konsumsi Antara',  span: 2 },
    { label: 'NTB (Juta Rp)',    span: 1, rowspan: 2 },
  ];
  cols1.forEach(c => {
    const th = document.createElement('th');
    th.textContent = c.label;
    th.colSpan = c.span;
    if (c.rowspan === 2) th.rowSpan = 2;
    if (c.class) th.className = c.class;
    r1.appendChild(th);
  });

  // Row 2: sub-headers
  const r2 = document.createElement('tr');
  r2.className = 'header-sub';
  ['Rasio (%)', 'Nilai (Jt)', 'Rasio (%)', 'Nilai (Jt)', 'Rasio (%)', 'Nilai (Jt)'].forEach(label => {
    const th = document.createElement('th');
    th.textContent = label;
    r2.appendChild(th);
  });

  thead.appendChild(r1);
  thead.appendChild(r2);
  return thead;
}


// ── Komoditas Row ─────────────────────────────────────────────────────────────

function buildKomoditasRow(row, no, basis) {
  const tr = document.createElement('tr');
  tr.className = rowClass(row);
  tr.dataset.komId = row.komoditas_id;
  tr.dataset.basis = basis;

  const isB = basis === 'adhb';
  const harga   = isB ? row.harga_berlaku    : row.harga_konstan_2010;
  const outU    = isB ? row.output_utama_adhb  : row.output_utama_adhk;
  const rasioOS = isB ? row.rasio_os_adhb     : row.rasio_os_adhk;
  const outI    = isB ? row.output_ikutan_adhb : row.output_ikutan_adhk;
  const rasioW  = isB ? row.rasio_wip_adhb    : row.rasio_wip_adhk;
  const wip     = isB ? row.wip_adhb          : row.wip_adhk;
  const primer  = isB ? row.output_primer_adhb : row.output_primer_adhk;
  const rasioKA = isB ? row.rasio_ka_adhb     : row.rasio_ka_adhk;
  const ka      = isB ? row.ka_adhb           : row.ka_adhk;
  const ntb     = isB ? row.ntb_adhb          : row.ntb_adhk;

  const ntbClass = (ntb !== null && parseFloat(ntb) < 0) ? ' val-negative' : '';

  tr.innerHTML = `
    <td class="col-sticky col-no ctr">${no}</td>
    <td class="col-sticky col-kom">
      <div style="font-size:0.81rem;font-weight:500">${row.komoditas_nama}</div>
      ${!row.has_data ? '<span style="font-size:0.68rem;color:var(--warn)">\u26a0 Data tidak lengkap</span>' : ''}
    </td>
    <td class="ctr" style="font-size:0.75rem;color:var(--text-muted)">${row.wujud_produksi || '\u2014'}</td>
    <td class="ctr" style="font-size:0.75rem;color:var(--text-muted)">${row.satuan_produksi || '\u2014'}</td>
    <td class="num">${row.kuantum !== null ? parseFloat(row.kuantum).toLocaleString('id-ID', {maximumFractionDigits:3}) : '<span class="val-missing">\u2014</span>'}</td>
    <td class="num">${harga !== null ? formatRupiah(harga, 0) : '<span class="val-missing">\u2014</span>'}</td>
    <td class="num" id="cell-${basis}-outU-${row.komoditas_id}">${cellVal(outU)}</td>
    <td class="pct">${rasioOS !== null ? `<span class="rasio-chip">${(rasioOS*100).toFixed(2)}%</span>` : '<span class="val-missing">\u2014</span>'}</td>
    <td class="num" id="cell-${basis}-outI-${row.komoditas_id}">${cellVal(outI)}</td>
    <td class="pct">${rasioW !== null ? `<span class="rasio-chip">${(rasioW*100).toFixed(2)}%</span>` : '<span class="val-missing">\u2014</span>'}</td>
    <td class="num" id="cell-${basis}-wip-${row.komoditas_id}">${cellVal(wip)}</td>
    <td class="num" id="cell-${basis}-prim-${row.komoditas_id}">${cellVal(primer)}</td>
    <td class="pct">${rasioKA !== null ? `<span class="rasio-chip">${(rasioKA*100).toFixed(2)}%</span>` : '<span class="val-missing">\u2014</span>'}</td>
    <td class="num" id="cell-${basis}-ka-${row.komoditas_id}">${cellVal(ka)}</td>
    <td class="num${ntbClass}" id="cell-${basis}-ntb-${row.komoditas_id}">${cellVal(ntb)}</td>
  `;
  return tr;
}


// ── Subtotal Rows ─────────────────────────────────────────────────────────────

function buildSubtotalRow(label, vals, extraClass = 'lk-row-subjumlah') {
  const tr = document.createElement('tr');
  tr.className = extraClass;
  // Count columns: 2 sticky + wujud + sat + kuantum + harga + outU + rasioOS + outI + rasioW + wip + primer + rasioKA + ka + ntb = 15
  const primer = vals.primer !== undefined ? vals.primer : (vals.sekunder !== undefined ? null : vals.lainnya);
  const span9 = '<td colspan="5"></td>';
  tr.innerHTML = `
    <td class="col-sticky col-no"></td>
    <td class="col-sticky col-kom" style="padding-left:8px;font-style:italic">${label}</td>
    ${span9}
    <td class="num">${vals.primer !== undefined ? cellVal(vals.primer) : cellVal(vals.sekunder !== undefined ? vals.sekunder : vals.lainnya)}</td>
    <td colspan="2"></td>
    <td class="num">${vals.primer !== undefined ? cellVal(vals.primer) : ''}</td>
    <td colspan="2"></td>
    <td></td>
  `;
  return tr;
}

function buildTotalRow(st, basis) {
  const isB = basis === 'adhb';
  const tr = document.createElement('tr');
  tr.className = 'lk-row-total';
  tr.id = `ws-total-row-${basis}`;
  const total  = isB ? st.output_total_adhb : st.output_total_adhk;
  const ka     = isB ? st.ka_adhb           : st.ka_adhk;
  const ntb    = isB ? st.ntb_adhb          : st.ntb_adhk;
  const rasioKA = null;   // rekap level rasio KA dihitung di level kategori

  const ntbClass = ntb !== null && parseFloat(ntb) < 0 ? ' val-negative' : '';

  tr.innerHTML = `
    <td class="col-sticky col-no"></td>
    <td class="col-sticky col-kom" style="font-weight:700;letter-spacing:0.02em">JUMLAH</td>
    <td colspan="4"></td>
    <td class="num">${cellVal(total)}</td>
    <td colspan="4"></td>
    <td class="num">${cellVal(total)}</td>
    <td class="pct"></td>
    <td class="num">${cellVal(ka)}</td>
    <td class="num${ntbClass}">${cellVal(ntb)}</td>
  `;
  return tr;
}


// ── Rekap Table ───────────────────────────────────────────────────────────────

function buildRekapTable(data) {
  const section = document.createElement('div');
  section.className = 'rekap-section';

  const header = document.createElement('div');
  header.className = 'rekap-header';
  header.innerHTML = `📑 REKAP — ${data.parent_nama} (${data.parent_kode})
    <span style="margin-left:auto;font-size:0.72rem;font-weight:400;opacity:0.7">
      ${data.tahun}${data.triwulan ? ' · TW'+['I','II','III','IV'][data.triwulan-1] : ' · Tahunan'}
    </span>`;
  section.appendChild(header);

  const table = document.createElement('table');
  table.className = 'rekap-table';

  // Header
  table.innerHTML = `
    <thead>
      <tr>
        <th style="width:36px">No</th>
        <th>Subkategori</th>
        <th class="num">NTB ADHB<br><small>(Juta Rp)</small></th>
        <th class="num">NTB ADHK<br><small>(Juta Rp)</small></th>
        <th class="num">Laju (%)</th>
        <th class="num">Indeks Implisit</th>
        <th class="num">Distribusi (%)</th>
      </tr>
    </thead>`;

  const tbody = document.createElement('tbody');
  data.rows.forEach(row => {
    const tr = document.createElement('tr');
    const ntbB = fmtJuta(row.ntb_adhb);
    const ntbK = fmtJuta(row.ntb_adhk);
    const laju  = row.laju_pertumbuhan_pct;
    const impl  = row.indeks_implisit;
    const dist  = row.distribusi_pct;

    tr.innerHTML = `
      <td class="ctr" style="color:var(--text-light);font-size:0.73rem">${row.no}</td>
      <td>
        <span style="font-size:0.72rem;color:var(--text-muted);font-family:var(--font-mono);margin-right:5px">${row.kategori_kode}</span>
        ${row.kategori_nama}
      </td>
      <td class="num">${ntbB !== null ? ntbB : '<span class="val-missing">\u2014</span>'}</td>
      <td class="num">${ntbK !== null ? ntbK : '<span class="val-missing">\u2014</span>'}</td>
      <td class="pct">${laju !== null ? growthBadge(laju) : '<span class="val-missing">\u2014</span>'}</td>
      <td class="num">${impl !== null ? fmtIndeks(impl) : '<span class="val-missing">\u2014</span>'}</td>
      <td class="pct">${dist !== null ? fmtIndeks(dist)+'%' : '<span class="val-missing">\u2014</span>'}</td>
    `;
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  // Footer total
  if (data.total) {
    const tfoot = document.createElement('tfoot');
    const tot = data.total;
    tfoot.innerHTML = `
      <tr>
        <td></td>
        <td><strong>TOTAL ${data.parent_kode}</strong></td>
        <td class="num">${tot.ntb_adhb !== null ? fmtJuta(tot.ntb_adhb) : '\u2014'}</td>
        <td class="num">${tot.ntb_adhk !== null ? fmtJuta(tot.ntb_adhk) : '\u2014'}</td>
        <td class="pct">${tot.laju_pertumbuhan_pct !== null ? growthBadge(tot.laju_pertumbuhan_pct) : ''}</td>
        <td class="num">${tot.indeks_implisit !== null ? fmtIndeks(tot.indeks_implisit) : '\u2014'}</td>
        <td class="pct">${tot.distribusi_pct !== null ? fmtIndeks(tot.distribusi_pct)+'%' : '\u2014'}</td>
      </tr>`;
    table.appendChild(tfoot);
  }

  section.appendChild(table);
  return section;
}


// ── Compare Table ─────────────────────────────────────────────────────────────

function buildCompareTable(compareData) {
  const wrap = document.createElement('div');
  wrap.style.cssText = 'overflow-x:auto;border:1px solid var(--border);border-top:none;background:var(--surface);border-radius:0 0 var(--radius) var(--radius)';

  const table = document.createElement('table');
  table.className = 'compare-table';
  table.innerHTML = `
    <thead>
      <tr>
        <th style="min-width:280px">Kategori</th>
        <th class="num adhb-col">NTB ADHB<br><small>(Juta Rp)</small></th>
        <th class="num adhk-col">NTB ADHK<br><small>(Juta Rp)</small></th>
        <th class="num impl-col">Indeks Implisit</th>
        <th class="num">Laju (%)</th>
        <th class="num">Distribusi (%)</th>
      </tr>
    </thead>`;

  const tbody = document.createElement('tbody');
  (compareData.rows || []).forEach(row => {
    const tr = document.createElement('tr');
    tr.className = `level-${row.level}`;
    const ntbB = fmtJuta(row.ntb_adhb);
    const ntbK = fmtJuta(row.ntb_adhk);
    tr.innerHTML = `
      <td style="padding-left:${(row.level-1)*16 + 10}px">
        <span style="font-size:0.68rem;color:var(--text-muted);font-family:var(--font-mono);margin-right:6px">${row.kategori_kode}</span>
        ${row.kategori_nama}
      </td>
      <td class="num adhb-col">${ntbB !== null ? ntbB : '<span class="val-missing">\u2014</span>'}</td>
      <td class="num adhk-col">${ntbK !== null ? ntbK : '<span class="val-missing">\u2014</span>'}</td>
      <td class="num impl-col">${row.indeks_implisit !== null ? fmtIndeks(row.indeks_implisit) : '<span class="val-missing">\u2014</span>'}</td>
      <td class="pct">${row.laju_pertumbuhan_pct !== null ? growthBadge(row.laju_pertumbuhan_pct) : '<span class="val-missing">\u2014</span>'}</td>
      <td class="pct">${row.distribusi_pct !== null ? fmtIndeks(row.distribusi_pct)+'%' : '<span class="val-missing">\u2014</span>'}</td>
    `;
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}


// ── SSE Targeted Cell Update ──────────────────────────────────────────────────

/**
 * Update specific cells when SSE pushes new calculation results.
 * @param {Array} updates - [{komoditas_id, ntb_adhb, ntb_adhk, ...}, ...]
 */
function updateWorksheetCells(updates) {
  if (!updates || !updates.length) return;

  updates.forEach(upd => {
    const id = upd.komoditas_id;
    if (!id) return;

    ['adhb', 'adhk'].forEach(basis => {
      const isB = basis === 'adhb';
      const fields = {
        outU:  isB ? upd.output_utama_adhb  : upd.output_utama_adhk,
        outI:  isB ? upd.output_ikutan_adhb : upd.output_ikutan_adhk,
        wip:   isB ? upd.wip_adhb           : upd.wip_adhk,
        prim:  null,  // recomputed below
        ka:    isB ? upd.ka_adhb            : upd.ka_adhk,
        ntb:   isB ? upd.ntb_adhb          : upd.ntb_adhk,
      };
      // Compute primer
      if (fields.outU !== undefined && fields.outI !== undefined && fields.wip !== undefined) {
        const p = (fields.outU||0) + (fields.outI||0) + (fields.wip||0);
        fields.prim = p || null;
      }

      Object.entries(fields).forEach(([key, val]) => {
        if (val === undefined) return;
        const cell = document.getElementById(`cell-${basis}-${key}-${id}`);
        if (!cell) return;

        const formatted = fmtJuta(val);
        cell.innerHTML = formatted !== null
          ? `<span class="val-readonly val-updated">${formatted}</span>`
          : '<span class="val-missing">\u2014</span>';

        // Flash row
        const row = cell.closest('tr');
        if (row) {
          row.classList.remove('lk-row-missing', 'lk-row-stale');
          row.classList.add('lk-row-updated');
          setTimeout(() => row.classList.remove('lk-row-updated'), 3100);
        }
      });
    });
  });
}


/**
 * Update total row after cascade.
 */
function updateTotalRow(subtotal, basis) {
  const totalRow = document.getElementById(`ws-total-row-${basis}`);
  if (!totalRow) return;
  const isB = basis === 'adhb';
  const total = isB ? subtotal.output_total_adhb : subtotal.output_total_adhk;
  const ka    = isB ? subtotal.ka_adhb           : subtotal.ka_adhk;
  const ntb   = isB ? subtotal.ntb_adhb          : subtotal.ntb_adhk;

  const cells = totalRow.querySelectorAll('td.num');
  // cells[0]=total, cells[1]=ka, cells[2]=ntb (approx — depends on structure)
  const totCell = totalRow.querySelector('[id^="ws-total-tot"]');
  // Rebuild total row content
  const ntbClass = ntb !== null && parseFloat(ntb) < 0 ? ' val-negative' : '';
  totalRow.innerHTML = `
    <td class="col-sticky col-no"></td>
    <td class="col-sticky col-kom" style="font-weight:700">JUMLAH</td>
    <td colspan="4"></td>
    <td class="num val-updated">${cellVal(total)}</td>
    <td colspan="4"></td>
    <td class="num val-updated">${cellVal(total)}</td>
    <td class="pct"></td>
    <td class="num val-updated">${cellVal(ka)}</td>
    <td class="num val-updated${ntbClass}">${cellVal(ntb)}</td>
  `;
}
