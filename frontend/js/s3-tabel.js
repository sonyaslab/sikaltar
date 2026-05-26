/**
 * s3-tabel.js — S3 Tabel Pokok PDRB
 * 6 tabel BPS: ADHB, ADHK, Distribusi, Laju, Indeks Implisit, Laju Implisit
 */

// ── State ─────────────────────────────────────────────────────────────────────
let s3Data = null;          // raw API response
let activeTabel = 'ntb_adhb';
const collapseState = {};   // {kode: bool} — true = collapsed

// ── Tabel metadata ─────────────────────────────────────────────────────────────
const TABEL_META = {
  ntb_adhb: {
    no: 1,
    title: 'Tabel 1 — PDRB Atas Dasar Harga Berlaku',
    subtitle: 'Satuan: Juta Rupiah',
    headerTitle: 'Tabel 1 — PDRB Atas Dasar Harga Berlaku (Juta Rupiah)',
    format: v => v == null ? '—' : fmtJuta(v),
    highlight: false,
  },
  ntb_adhk: {
    no: 2,
    title: 'Tabel 2 — PDRB Atas Dasar Harga Konstan 2010',
    subtitle: 'Satuan: Juta Rupiah',
    headerTitle: 'Tabel 2 — PDRB Atas Dasar Harga Konstan 2010 (Juta Rupiah)',
    format: v => v == null ? '—' : fmtJuta(v),
    highlight: false,
  },
  distribusi_pct: {
    no: 3,
    title: 'Tabel 3 — Distribusi Persentase ADHB',
    subtitle: 'Satuan: Persen (%)',
    headerTitle: 'Tabel 3 — Distribusi Persentase PDRB ADHB (%)',
    format: v => v == null ? '—' : fmtPct(v),
    highlight: false,
  },
  laju_pertumbuhan_pct: {
    no: 4,
    title: 'Tabel 4 — Laju Pertumbuhan ADHK',
    subtitle: 'Satuan: Persen (%)',
    headerTitle: 'Tabel 4 — Laju Pertumbuhan PDRB ADHK (%)',
    format: v => v == null ? '-' : fmtPct(v),
    highlight: true,  // merah negatif, hijau > 10
  },
  indeks_implisit: {
    no: 5,
    title: 'Tabel 5 — Indeks Implisit',
    subtitle: 'Basis 2010 = 100,00',
    headerTitle: 'Tabel 5 — Indeks Implisit PDRB (2010=100)',
    format: v => v == null ? '—' : fmtPct(v),
    highlight: false,
  },
  laju_implisit_pct: {
    no: 6,
    title: 'Tabel 6 — Laju Perubahan Indeks Implisit',
    subtitle: 'Satuan: Persen (%)',
    headerTitle: 'Tabel 6 — Laju Perubahan Indeks Implisit (%)',
    format: v => v == null ? '-' : fmtPct(v),
    highlight: true,
  },
};

// ── Format helpers ─────────────────────────────────────────────────────────────
function fmtJuta(v) {
  if (v == null) return '—';
  return parseFloat(v).toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtPct(v) {
  if (v == null) return '-';
  return parseFloat(v).toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function showToast(msg, type = 'info') {
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  document.getElementById('toast-container').appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Init ───────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  await loadWilayah();
  setDefaultTahun();
  bindEvents();
  await loadData();
});

async function loadWilayah() {
  const sel = document.getElementById('f-wilayah');
  try {
    const data = await apiFetch('/wilayah');
    sel.innerHTML = '';
    data.forEach(w => {
      const opt = document.createElement('option');
      opt.value = w.kode;
      opt.textContent = `${w.nama}${w.level === 'provinsi' ? ' (Provinsi)' : ''}`;
      if (w.level === 'provinsi') opt.selected = true;
      sel.appendChild(opt);
    });
  } catch {
    sel.innerHTML = '<option value="65">Provinsi Kaltara</option>';
  }
}

function setDefaultTahun() {
  const now = new Date().getFullYear();
  document.getElementById('f-tahun-akhir').value = now - 1;
}

function bindEvents() {
  // Tab nav
  document.querySelectorAll('.tabel-nav-btn[data-tabel]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tabel-nav-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeTabel = btn.dataset.tabel;
      renderTabel();
    });
  });

  document.getElementById('btn-muat').addEventListener('click', loadData);
  document.getElementById('btn-collapse-all').addEventListener('click', collapseAll);
  document.getElementById('btn-expand-all').addEventListener('click', expandAll);
  document.getElementById('btn-export').addEventListener('click', exportExcel);

  document.getElementById('f-tahun-awal').addEventListener('change', () => {
    const a = +document.getElementById('f-tahun-awal').value;
    const b = +document.getElementById('f-tahun-akhir').value;
    if (b < a) document.getElementById('f-tahun-akhir').value = a;
  });
}

// ── Load data from API ─────────────────────────────────────────────────────────
async function loadData() {
  const wilayah = document.getElementById('f-wilayah').value;
  const ta = document.getElementById('f-tahun-awal').value;
  const tb = document.getElementById('f-tahun-akhir').value;

  setLoading(true);
  try {
    s3Data = await apiFetch(`/s3/tabel-pokok?wilayah_kode=${wilayah}&tahun_awal=${ta}&tahun_akhir=${tb}`);
    document.getElementById('s3-last-updated').textContent =
      `Data dimuat: ${new Date().toLocaleTimeString('id-ID')}`;
    renderTabel();
  } catch (err) {
    showToast('Gagal memuat data: ' + err.message, 'error');
    setLoading(false);
  }
}

function setLoading(show) {
  document.getElementById('tabel-loading').style.display = show ? 'flex' : 'none';
  document.getElementById('tabel-container').style.display = show ? 'none' : 'block';
}

// ── Render ─────────────────────────────────────────────────────────────────────
function renderTabel() {
  if (!s3Data) return;
  const meta = TABEL_META[activeTabel];

  document.getElementById('s3-header-title').textContent = meta.headerTitle;
  document.getElementById('tabel-card-title').textContent = meta.title;
  document.getElementById('tabel-card-subtitle').textContent = meta.subtitle;

  const { tahun_list, kategori, tabel, total } = s3Data;
  const tableData = tabel[activeTabel];
  const totalData = total[activeTabel];

  // Build kategori hierarchy: level-1 → contains children
  const level1 = kategori.filter(k => k.level === 1);
  const childOf = {};
  kategori.forEach(k => {
    if (k.parent_kode) {
      childOf[k.parent_kode] = childOf[k.parent_kode] || [];
      childOf[k.parent_kode].push(k);
    }
  });

  const wrap = document.getElementById('tabel-container');
  wrap.innerHTML = '';

  const table = document.createElement('table');
  table.className = 'tabel-pokok';
  table.id = `tp-${activeTabel}`;

  // ── THEAD ──
  const thead = document.createElement('thead');
  const tr1 = document.createElement('tr');
  const thNo = document.createElement('th');
  thNo.className = 'col-no'; thNo.textContent = 'No.'; thNo.rowSpan = 2;
  const thNama = document.createElement('th');
  thNama.className = 'col-nama'; thNama.textContent = 'Kategori / Lapangan Usaha'; thNama.rowSpan = 2;
  tr1.appendChild(thNo); tr1.appendChild(thNama);
  tahun_list.forEach(t => {
    const th = document.createElement('th');
    th.textContent = t; th.style.minWidth = '90px'; th.style.textAlign = 'center';
    tr1.appendChild(th);
  });
  thead.appendChild(tr1);

  const tr2 = document.createElement('tr');
  tr2.className = 'sub-header';
  tahun_list.forEach(() => {
    const th = document.createElement('th');
    th.textContent = meta.no <= 2 ? '(Juta Rp)' : meta.no <= 4 || meta.no === 6 ? '(%)' : '(2010=100)';
    thead.appendChild(tr2);
    tr2.appendChild(th);
  });
  thead.appendChild(tr2);
  table.appendChild(thead);

  // ── TBODY ──
  const tbody = document.createElement('tbody');
  let rowNo = 0;

  level1.forEach(l1 => {
    rowNo++;
    const isCollapsed = collapseState[l1.kode] === true;
    const children = childOf[l1.kode] || [];

    // Level-1 row
    const tr = makeTr(l1, rowNo, tahun_list, tableData, meta, 1, children.length > 0, isCollapsed);
    tbody.appendChild(tr);

    // Level-2 children
    children.forEach((l2, l2i) => {
      const tr2r = makeTr(l2, `${rowNo}.${l2i + 1}`, tahun_list, tableData, meta, 2, false, false, isCollapsed, l1.kode);
      tbody.appendChild(tr2r);

      // Level-3 grandchildren
      const grandkids = childOf[l2.kode] || [];
      grandkids.forEach((l3, l3i) => {
        const tr3r = makeTr(l3, `${rowNo}.${l2i + 1}.${String.fromCharCode(97 + l3i)}`, tahun_list, tableData, meta, 3, false, false, isCollapsed, l1.kode);
        tbody.appendChild(tr3r);
      });
    });
  });

  // TOTAL row
  const trTot = document.createElement('tr');
  trTot.className = 'row-total';
  const tdNo = document.createElement('td'); tdNo.className = 'col-no'; tdNo.textContent = ''; trTot.appendChild(tdNo);
  const tdNama = document.createElement('td'); tdNama.className = 'col-nama'; tdNama.textContent = 'PDRB'; trTot.appendChild(tdNama);
  tahun_list.forEach(t => {
    const td = document.createElement('td');
    const v = totalData ? totalData[String(t)] ?? totalData[t] : null;
    td.className = 'num';
    td.textContent = meta.format(v);
    trTot.appendChild(td);
  });
  tbody.appendChild(trTot);

  table.appendChild(tbody);
  wrap.appendChild(table);
  setLoading(false);
}

function makeTr(kat, no, tahun_list, tableData, meta, level, hasChildren, isCollapsed, parentCollapsed = false, parentKode = null) {
  const tr = document.createElement('tr');
  tr.className = `row-level${level}`;
  tr.dataset.kode = kat.kode;
  if (parentKode) tr.dataset.parent = parentKode;
  if (level > 1 && parentCollapsed) tr.classList.add('hidden');

  const tdNo = document.createElement('td');
  tdNo.className = 'col-no';
  tdNo.textContent = no;
  tr.appendChild(tdNo);

  const tdNama = document.createElement('td');
  tdNama.className = `col-nama${level === 2 ? ' indent-l2' : level === 3 ? ' indent-l3' : ''}`;
  if (hasChildren) {
    const icon = document.createElement('i');
    icon.className = 'collapse-icon';
    icon.textContent = '▼';
    if (isCollapsed) { tr.classList.add('collapsed'); }
    tdNama.appendChild(icon);
    tdNama.addEventListener('click', () => toggleCollapse(kat.kode, tr));
  }
  const singkat = kat.kode_singkat ? ` (${kat.kode_singkat})` : '';
  tdNama.appendChild(document.createTextNode(kat.nama + (level === 1 ? singkat : '')));
  tr.appendChild(tdNama);

  const katData = tableData ? tableData[kat.kode] : null;
  tahun_list.forEach(t => {
    const td = document.createElement('td');
    const v = katData ? katData[t] : null;
    if (v == null) {
      td.className = 'dash'; td.textContent = meta.format(v);
    } else {
      td.className = 'num'; td.textContent = meta.format(v);
      if (meta.highlight) {
        const n = parseFloat(v);
        if (n < 0) td.classList.add('hl-neg');
        else if (n > 10) td.classList.add('hl-high');
      }
    }
    tr.appendChild(td);
  });

  return tr;
}

// ── Collapse/Expand ────────────────────────────────────────────────────────────
function toggleCollapse(kode, headerRow) {
  const collapsed = !collapseState[kode];
  collapseState[kode] = collapsed;
  if (collapsed) headerRow.classList.add('collapsed');
  else headerRow.classList.remove('collapsed');

  document.querySelectorAll(`tr[data-parent="${kode}"]`).forEach(tr => {
    if (collapsed) tr.classList.add('hidden');
    else tr.classList.remove('hidden');
  });
}

function collapseAll() {
  if (!s3Data) return;
  s3Data.kategori.filter(k => k.level === 1).forEach(k => { collapseState[k.kode] = true; });
  renderTabel();
}
function expandAll() {
  if (!s3Data) return;
  s3Data.kategori.filter(k => k.level === 1).forEach(k => { collapseState[k.kode] = false; });
  renderTabel();
}

// ── Export Excel (SheetJS) ────────────────────────────────────────────────────
function exportExcel() {
  if (!s3Data) { showToast('Muat data terlebih dahulu', 'warn'); return; }
  const meta = TABEL_META[activeTabel];
  const { tahun_list, kategori, tabel, total } = s3Data;
  const tableData = tabel[activeTabel];
  const totalData = total[activeTabel];

  const wsData = [];
  // Header BPS style
  wsData.push(['PDRB KALIMANTAN UTARA']);
  wsData.push([meta.title]);
  wsData.push([meta.subtitle]);
  wsData.push([]);
  // Column headers
  wsData.push(['No.', 'Lapangan Usaha / Kategori', ...tahun_list]);

  // Rows
  let no = 0;
  kategori.filter(k => k.level === 1).forEach(l1 => {
    no++;
    const l1data = tableData[l1.kode] || {};
    wsData.push([no, l1.nama, ...tahun_list.map(t => l1data[t] ?? null)]);
    const children = kategori.filter(k => k.parent_kode === l1.kode);
    children.forEach((l2, i) => {
      const l2data = tableData[l2.kode] || {};
      wsData.push([`${no}.${i + 1}`, `  ${l2.nama}`, ...tahun_list.map(t => l2data[t] ?? null)]);
    });
  });
  // Total
  wsData.push(['', 'PDRB', ...tahun_list.map(t => totalData ? (totalData[String(t)] ?? totalData[t] ?? null) : null)]);

  const ws = XLSX.utils.aoa_to_sheet(wsData);
  // Freeze pane at column C (after No + Nama)
  ws['!freeze'] = { xSplit: 2, ySplit: 5 };
  ws['!cols'] = [{ wch: 6 }, { wch: 46 }, ...tahun_list.map(() => ({ wch: 16 }))];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, `Tabel ${meta.no}`);
  XLSX.writeFile(wb, `PDRB_Kaltara_Tabel${meta.no}_${activeTabel}.xlsx`);
  showToast(`Export Excel berhasil — Tabel ${meta.no}`, 'success');
}
