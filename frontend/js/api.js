/**
 * api.js — SIKALTARA API Client
 * Fetch wrapper dengan error handling, toast notification, dan retry.
 */

const API_BASE = '';   // FastAPI sama port, prefix /api

const SUMBER_DATA_OPTIONS = [
  '', 'BPS', 'Dinas Pertanian', 'Dinas Kehutanan', 'Dinas ESDM',
  'Dinas Perikanan', 'Survei Lapangan', 'Estimasi', 'Dinas Peternakan',
  'PLN', 'Pertamina', 'Data Primer', 'Lainnya',
];

/** Fetch JSON dari endpoint API. Otomatis menyertakan JWT Bearer token. */
async function apiFetch(path, options = {}) {
  const url   = `${API_BASE}/api${path}`;
  const token = localStorage.getItem('sikaltar_token');

  const defaults = {
    headers: {
      'Content-Type':  'application/json',
      'Accept':        'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
  };

  const config = {
    ...defaults,
    ...options,
    headers: { ...defaults.headers, ...(options.headers || {}) },
  };

  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  const res = await fetch(url, config);

  // Token expired / invalid → redirect ke login
  if (res.status === 401) {
    localStorage.removeItem('sikaltar_token');
    localStorage.removeItem('sikaltar_role');
    localStorage.removeItem('sikaltar_wilayah');
    localStorage.removeItem('sikaltar_nama');
    window.location.href = '/app/login.html';
    return;
  }

  if (!res.ok) {
    let errMsg = `HTTP ${res.status}`;
    try {
      const errBody = await res.json();
      errMsg = errBody.detail || errMsg;
    } catch {}
    throw new ApiError(res.status, errMsg);
  }
  return res.json();
}

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

/** GET /api/wilayah */
async function getWilayah() {
  return apiFetch('/wilayah');
}

/** GET /api/komoditas/hierarki */
async function getHierarki() {
  return apiFetch('/komoditas/hierarki');
}

/** GET /api/input/harga?wilayah_kode=...&tahun=...&triwulan=... */
async function getHarga(wilayahKode, tahun, triwulan) {
  const q = buildQuery({ wilayah_kode: wilayahKode, tahun, triwulan });
  return apiFetch(`/input/harga?${q}`);
}

/** PATCH /api/input/harga/{komoditas_id} */
async function patchHarga(komoditasId, wilayahKode, tahun, triwulan, body) {
  const q = buildQuery({ wilayah_kode: wilayahKode, tahun, triwulan });
  return apiFetch(`/input/harga/${komoditasId}?${q}`, {
    method: 'PATCH', body,
  });
}

/** GET /api/input/produksi */
async function getProduksi(wilayahKode, tahun, triwulan) {
  const q = buildQuery({ wilayah_kode: wilayahKode, tahun, triwulan });
  return apiFetch(`/input/produksi?${q}`);
}

/** PATCH /api/input/produksi/{komoditas_id} */
async function patchProduksi(komoditasId, wilayahKode, tahun, triwulan, body) {
  const q = buildQuery({ wilayah_kode: wilayahKode, tahun, triwulan });
  return apiFetch(`/input/produksi/${komoditasId}?${q}`, {
    method: 'PATCH', body,
  });
}

/** GET /api/rasio */
async function getRasio(jenisRasio, tahun, berlakuUntuk, wilayahKode) {
  const q = buildQuery({ jenis_rasio: jenisRasio, tahun, berlaku_untuk: berlakuUntuk, wilayah_kode: wilayahKode });
  return apiFetch(`/rasio?${q}`);
}

/** GET /api/rasio/impact-preview */
async function getRasioImpactPreview(params) {
  const q = buildQuery(params);
  return apiFetch(`/rasio/impact-preview?${q}`);
}

/** POST /api/rasio/override */
async function postRasioOverride(body) {
  return apiFetch('/rasio/override', { method: 'POST', body });
}

/** DELETE /api/rasio/override/{id} */
async function deleteRasioOverride(overrideId) {
  return apiFetch(`/rasio/override/${overrideId}`, { method: 'DELETE' });
}

/** GET /api/input/deflator */
async function getDeflator(wilayahKode, tahun, triwulan) {
  const q = buildQuery({ wilayah_kode: wilayahKode, tahun, triwulan });
  return apiFetch(`/input/deflator?${q}`);
}

/** PATCH /api/input/deflator/{kategori_kode} */
async function patchDeflator(kategoriKode, wilayahKode, tahun, triwulan, body) {
  const q = buildQuery({ wilayah_kode: wilayahKode, tahun, triwulan });
  return apiFetch(`/input/deflator/${encodeURIComponent(kategoriKode)}?${q}`, {
    method: 'PATCH', body,
  });
}

/** Build URL query string, skip null/undefined values. */
function buildQuery(params) {
  return Object.entries(params)
    .filter(([, v]) => v !== null && v !== undefined)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');
}

/** Format Decimal: Rp 1.234.567 */
function formatRupiah(val, decimals = 0) {
  if (val === null || val === undefined || val === '') return '—';
  const n = parseFloat(val);
  if (isNaN(n)) return '—';
  return n.toLocaleString('id-ID', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/** Format Decimal as percentage: 0.1516 → '15,16%' */
function formatPersen(val) {
  if (val === null || val === undefined || val === '') return '—';
  const n = parseFloat(val) * 100;
  if (isNaN(n)) return '—';
  return `${n.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}%`;
}

/** Format kuantum dengan satuan. */
function formatKuantum(val, satuan = '') {
  if (val === null || val === undefined || val === '') return '';
  const n = parseFloat(val);
  if (isNaN(n)) return '';
  return `${n.toLocaleString('id-ID', { maximumFractionDigits: 3 })}`;
}
