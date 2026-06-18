/**
 * mdm-api.js — MDM API Helper
 * Wrapper fetch untuk semua endpoint /api/mdm/*
 */
'use strict';

const MDM_BASE = '/api/mdm';

// Shared auth header — JWT Bearer token from localStorage (same as api.js)
function _mdmHeaders(extra = {}) {
  const token = localStorage.getItem('sikaltar_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    'X-MDM-User': sessionStorage.getItem('mdm_user') || 'Admin',
    ...extra,
  };
}

async function _mdmFetch(url, opts = {}) {
  const res = await fetch(url, { headers: _mdmHeaders(), ...opts });
  // Token expired / invalid → redirect ke login (same as api.js)
  if (res.status === 401) {
    localStorage.removeItem('sikaltar_token');
    localStorage.removeItem('sikaltar_role');
    localStorage.removeItem('sikaltar_wilayah');
    localStorage.removeItem('sikaltar_nama');
    window.location.href = '/app/login.html';
    return;
  }
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { const j = await res.json(); msg = j.detail || msg; } catch {}
    throw new Error(msg);
  }
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return res.text();
}

// ─── Kategori ──────────────────────────────────────────────────────────

function mdmGetKategori(params = {}) {
  const q = new URLSearchParams({aktif_only: true, ...params});
  return _mdmFetch(`${MDM_BASE}/kategori?${q}`);
}
function mdmGetKategoriDetail(kode) {
  return _mdmFetch(`${MDM_BASE}/kategori/${kode}`);
}
function mdmCreateKategori(data, userNama = 'Admin') {
  return _mdmFetch(`${MDM_BASE}/kategori?user_nama=${encodeURIComponent(userNama)}`, {
    method: 'POST', body: JSON.stringify(data),
  });
}
function mdmUpdateKategori(kode, data, userNama = 'Admin', confirmMetode = false) {
  const q = new URLSearchParams({ user_nama: userNama, confirm_metode: confirmMetode });
  return _mdmFetch(`${MDM_BASE}/kategori/${kode}?${q}`, {
    method: 'PUT', body: JSON.stringify(data),
  });
}
function mdmDeleteKategori(kode, alasan, userNama = 'Admin') {
  const q = new URLSearchParams({ alasan, user_nama: userNama });
  return _mdmFetch(`${MDM_BASE}/kategori/${kode}?${q}`, { method: 'DELETE' });
}
function mdmGetMetodeOptions() {
  return _mdmFetch(`${MDM_BASE}/kategori/metode-options`);
}

// ─── Komoditas ────────────────────────────────────────────────────────

function mdmGetKomoditas(params = {}) {
  const q = new URLSearchParams({status: 'aktif', per_page: 100, ...params});
  return _mdmFetch(`${MDM_BASE}/komoditas?${q}`);
}
function mdmGetKomoditasDetail(id) {
  return _mdmFetch(`${MDM_BASE}/komoditas/${id}?include_audit=true`);
}
function mdmGetKomoditasStats() {
  return _mdmFetch(`${MDM_BASE}/komoditas/stats`);
}
function mdmCreateKomoditas(data, userNama = 'Admin') {
  return _mdmFetch(`${MDM_BASE}/komoditas?user_nama=${encodeURIComponent(userNama)}`, {
    method: 'POST', body: JSON.stringify(data),
  });
}
function mdmUpdateKomoditas(id, data, userNama = 'Admin') {
  return _mdmFetch(`${MDM_BASE}/komoditas/${id}?user_nama=${encodeURIComponent(userNama)}`, {
    method: 'PUT', body: JSON.stringify(data),
  });
}
function mdmNonaktifkanKomoditas(id, alasan, userNama = 'Admin') {
  const q = new URLSearchParams({ alasan, user_nama: userNama });
  return _mdmFetch(`${MDM_BASE}/komoditas/${id}/nonaktifkan?${q}`, { method: 'POST' });
}
async function mdmPreviewImport(file, kategoriKode = null) {
  const fd = new FormData();
  fd.append('file', file);
  const q = kategoriKode ? `?kategori_kode=${kategoriKode}` : '';
  const res = await fetch(`${MDM_BASE}/komoditas/import/preview${q}`, { method: 'POST', body: fd });
  if (!res.ok) { const j = await res.json(); throw new Error(j.detail || 'Import error'); }
  return res.json();
}
async function mdmApplyImport(file, opts = {}) {
  const fd = new FormData();
  fd.append('file', file);
  const q = new URLSearchParams({
    apply_new: opts.applyNew ?? true,
    apply_changed: opts.applyChanged ?? true,
    user_nama: opts.userNama || 'Admin',
    ...(opts.kategoriKode ? {kategori_kode: opts.kategoriKode} : {}),
  });
  const res = await fetch(`${MDM_BASE}/komoditas/import/apply?${q}`, { method: 'POST', body: fd });
  if (!res.ok) { const j = await res.json(); throw new Error(j.detail || 'Apply error'); }
  return res.json();
}

// ─── Klasifikasi ──────────────────────────────────────────────────────

function mdmGetVersi() { return _mdmFetch(`${MDM_BASE}/klasifikasi/versi`); }
function mdmGetMapping(versi = 'kbli_2009', kategoriKode = null) {
  const q = new URLSearchParams({ versi, ...(kategoriKode ? {kategori_kode: kategoriKode} : {}) });
  return _mdmFetch(`${MDM_BASE}/klasifikasi/mapping?${q}`);
}
function mdmGetGapAnalysis(versi = 'kbli_2009') {
  return _mdmFetch(`${MDM_BASE}/klasifikasi/gap-analysis?versi=${versi}`);
}

// ─── Satuan ───────────────────────────────────────────────────────────

function mdmGetSatuan() { return _mdmFetch(`${MDM_BASE}/satuan`); }
function mdmCreateSatuan(data, userNama = 'Admin') {
  return _mdmFetch(`${MDM_BASE}/satuan?user_nama=${encodeURIComponent(userNama)}`, {
    method: 'POST', body: JSON.stringify(data),
  });
}
function mdmUpdateSatuan(id, data, userNama = 'Admin') {
  return _mdmFetch(`${MDM_BASE}/satuan/${id}?user_nama=${encodeURIComponent(userNama)}`, {
    method: 'PUT', body: JSON.stringify(data),
  });
}
function mdmDeleteSatuan(id, alasan, userNama = 'Admin') {
  const q = new URLSearchParams({ alasan, user_nama: userNama });
  return _mdmFetch(`${MDM_BASE}/satuan/${id}?${q}`, { method: 'DELETE' });
}

// ─── Faktor Konversi ──────────────────────────────────────────────────

function mdmGetFaktorKonversi(q = null) {
  const url = q ? `${MDM_BASE}/faktor-konversi?q=${encodeURIComponent(q)}` : `${MDM_BASE}/faktor-konversi`;
  return _mdmFetch(url);
}
function mdmGetFaktorHistory(komoditasId) {
  return _mdmFetch(`${MDM_BASE}/faktor-konversi/${komoditasId}/history`);
}
function mdmUpdateFaktor(komoditasId, data, userNama = 'Admin') {
  return _mdmFetch(`${MDM_BASE}/faktor-konversi/${komoditasId}?user_nama=${encodeURIComponent(userNama)}`, {
    method: 'PUT', body: JSON.stringify(data),
  });
}
function mdmTriggerRecalc(komoditasId, tahunMulai, tahunAkhir, userNama = 'Admin') {
  const q = new URLSearchParams({ tahun_mulai: tahunMulai, tahun_akhir: tahunAkhir, user_nama: userNama });
  return _mdmFetch(`${MDM_BASE}/faktor-konversi/${komoditasId}/recalc?${q}`, { method: 'POST' });
}

// ─── Audit Log ─────────────────────────────────────────────────────────

function mdmGetAudit(params = {}) {
  const q = new URLSearchParams({per_page: 50, page: 1, ...params});
  return _mdmFetch(`${MDM_BASE}/audit?${q}`);
}
function mdmGetRecordAudit(tabel, recordId) {
  return _mdmFetch(`${MDM_BASE}/audit/record/${tabel}/${recordId}`);
}
function mdmExportAudit(params = {}) {
  const q = new URLSearchParams(params);
  window.open(`${MDM_BASE}/audit/export?${q}`, '_blank');
}
