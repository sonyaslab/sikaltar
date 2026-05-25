/**
 * s2-api.js — S2 Lembar Kerja API helpers
 * Semua call ke /api/s2/* endpoint
 */

/** GET /api/s2/worksheet */
async function getWorksheet(wilayahKode, tahun, triwulan, kategoriKode) {
  const q = buildQuery({ wilayah_kode: wilayahKode, tahun, triwulan, kategori_kode: kategoriKode });
  return apiFetch(`/s2/worksheet?${q}`);
}

/** GET /api/s2/rekap */
async function getRekap(wilayahKode, tahun, triwulan, parentKode) {
  const q = buildQuery({ wilayah_kode: wilayahKode, tahun, triwulan, parent_kode: parentKode });
  return apiFetch(`/s2/rekap?${q}`);
}

/** GET /api/s2/status */
async function getS2Status(wilayahKode, tahun, triwulan) {
  const q = buildQuery({ wilayah_kode: wilayahKode, tahun, triwulan });
  return apiFetch(`/s2/status?${q}`);
}

/** GET /api/s2/compare */
async function getCompare(wilayahKode, tahun, triwulan, parentKode = '') {
  const q = buildQuery({ wilayah_kode: wilayahKode, tahun, triwulan, parent_kode: parentKode });
  return apiFetch(`/s2/compare?${q}`);
}


// ── Formatting helpers for S2 (read-only display) ─────────────────────────────

/** Format number as Juta Rp: 1234567.89 → '1.234.567,89' */
function fmtJuta(val, decimals = 2) {
  if (val === null || val === undefined) return null;
  const n = parseFloat(val);
  if (isNaN(n)) return null;
  return n.toLocaleString('id-ID', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/** Format as percentage: 0.15 → '15,00%' */
function fmtPct(val, decimals = 2) {
  if (val === null || val === undefined) return null;
  const n = parseFloat(val) * 100;
  if (isNaN(n)) return null;
  return n.toLocaleString('id-ID', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: 4,
  }) + '%';
}

/** Format rasio as percent string: 0.1516 → '15,16%' */
function fmtRasio(val) {
  return fmtPct(val, 2);
}

/** Format growth rate with sign: 3.45 → '+3,45%' */
function fmtGrowth(val) {
  if (val === null || val === undefined) return null;
  const n = parseFloat(val);
  if (isNaN(n)) return null;
  const sign = n > 0 ? '+' : '';
  return sign + n.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) + '%';
}

/** Format implicit index: 123.45 */
function fmtIndeks(val) {
  if (val === null || val === undefined) return null;
  const n = parseFloat(val);
  if (isNaN(n)) return null;
  return n.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
}

/** Render a cell value (null → missing placeholder) */
function cellVal(val, formatter = fmtJuta, { decimals } = {}) {
  const formatted = decimals !== undefined ? formatter(val, decimals) : formatter(val);
  if (formatted === null) {
    return '<span class="val-missing">—</span>';
  }
  return `<span class="val-readonly">${formatted}</span>`;
}

/** Determine row class from row data */
function rowClass(row) {
  if (!row.has_data) return 'lk-row-missing';
  if (row.has_error) return 'lk-row-error';
  if (row.is_valid === false) return 'lk-row-stale';
  return 'lk-row-normal';
}

/** Get growth indicator badge HTML */
function growthBadge(val) {
  if (val === null || val === undefined) return '';
  const n = parseFloat(val);
  const cls = n > 0 ? 'ind-pos' : (n < 0 ? 'ind-neg' : 'ind-zero');
  const sign = n > 0 ? '▲' : (n < 0 ? '▼' : '—');
  return `<span class="ind-badge ${cls}">${sign} ${Math.abs(n).toFixed(2)}%</span>`;
}
