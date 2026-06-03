/**
 * master-komoditas.js — Controller untuk halaman Master Data Komoditas
 * Mendukung hierarchical grouping, inline editing, dan audit logging.
 */
'use strict';

let allData = [];
let collapsedGroups = new Set();
let currentEditing = null; // { id, field, originalValue, element }
let satuanOptions = [];
let kategoriOptions = [];

// DOM Elements
const tableBody = document.getElementById('table-body');
const filterName = document.getElementById('search-name');
const filterKat = document.getElementById('filter-kategori');
const filterStatus = document.getElementById('filter-status');
const filterKbli = document.getElementById('filter-kbli');

// Initialization
window.addEventListener('DOMContentLoaded', async () => {
    await Promise.all([
        loadSatuan(),
        loadKategori(),
        fetchData()
    ]);

    // Setup Filters
    if (filterName) {
        filterName.addEventListener('change', fetchData);
        filterName.addEventListener('keyup', debounce(fetchData, 500));
    }
    if (filterKat) filterKat.addEventListener('change', fetchData);
    if (filterStatus) filterStatus.addEventListener('change', fetchData);
    if (filterKbli) {
        filterKbli.addEventListener('change', fetchData);
        filterKbli.addEventListener('keyup', debounce(fetchData, 500));
    }
});

// ─── Data Loading ────────────────────────────────────────────────────────────

async function fetchData() {
    const params = new URLSearchParams({
        q: filterName?.value || '',
        kategori: filterKat?.value || '',
        status: filterStatus?.value || 'aktif',
        kbli: filterKbli?.value || ''
    });

    try {
        const res = await fetch(`/api/master/komoditas?${params}`);
        if (!res.ok) throw new Error('Gagal memuat data');
        allData = await res.json();
        renderTable();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function loadSatuan() {
    try {
        const res = await fetch('/api/mdm/satuan');
        const data = await res.json();
        satuanOptions = data;
        const sel = document.getElementById('new-satuan');
        const detSel = document.getElementById('det-satuan');
        const opts = data.map(s => `<option value="${s.nama}">${s.nama}</option>`).join('');
        if (sel) sel.innerHTML = opts;
        if (detSel) detSel.innerHTML = opts;
    } catch (err) {}
}

async function loadKategori() {
    try {
        const data = await mdmGetKategori();
        kategoriOptions = data;
        const filterSel = document.getElementById('filter-kategori');
        const addSel = document.getElementById('new-kategori');
        const detSel = document.getElementById('det-kategori');

        const opts = data.map(k => `<option value="${k.kode}">${k.kode} ${k.nama}</option>`).join('');
        if (filterSel) filterSel.innerHTML += opts;
        if (addSel) addSel.innerHTML = opts;
        if (detSel) detSel.innerHTML = opts;
    } catch (err) {}
}

// ─── Rendering ───────────────────────────────────────────────────────────────

function renderTable() {
    if (!tableBody) return;
    if (!allData.length) {
        tableBody.innerHTML = '<tr><td colspan="20" style="text-align:center; padding:40px">Data tidak ditemukan</td></tr>';
        return;
    }

    let html = '';
    let visibleRows = [];

    allData.forEach(item => {
        let isVisible = true;
        if (item.type === 'komoditas' || item.type === 'slot') {
            const parts = item.kategori_kode.split('.');
            if (collapsedGroups.has(parts[0]) ||
                collapsedGroups.has(`${parts[0]}.${parts[1]}`) ||
                collapsedGroups.has(item.kategori_kode)) {
                isVisible = false;
            }
        } else if (item.type === 'group') {
            const parts = item.kode.split('.');
            if (item.level === 2 && collapsedGroups.has(parts[0])) isVisible = false;
            if (item.level === 3 && (collapsedGroups.has(parts[0]) || collapsedGroups.has(`${parts[0]}.${parts[1]}`))) isVisible = false;
        }
        if (isVisible) visibleRows.push(item);
    });

    visibleRows.forEach((row, idx) => {
        if (row.type === 'group') html += renderGroupRow(row);
        else if (row.type === 'komoditas') html += renderKomoditasRow(row, idx);
        else if (row.type === 'slot') html += renderSlotRow(row);
    });
    tableBody.innerHTML = html;
}

function renderGroupRow(row) {
    const isCollapsed = collapsedGroups.has(row.kode);
    const icon = isCollapsed ? '▶️' : '▼';
    return `
        <tr class="row-l${row.level}">
            <td colspan="2" class="indent-l${row.level}">
                <span class="toggle-icon" onclick="toggleGroup('${row.kode}')">${icon}</span>
                ${row.kode} ${row.nama}
            </td>
            <td colspan="17"></td>
            <td style="text-align:right">
                <span class="badge ${row.count_aktif > 0 ? 'badge-green' : 'badge-gray'}">${row.count_aktif} aktif</span>
            </td>
        </tr>
    `;
}

function renderKomoditasRow(row, idx) {
    const statusClass = row.aktif ? '' : 'inactive';
    return `
        <tr class="row-l4 ${statusClass}" data-id="${row.id}">
            <td style="text-align:center; color:#94a3b8">${row.kode_internal}</td>
            <td class="editable-cell indent-l4" data-field="nama">${row.nama}</td>
            <td class="editable-cell" data-field="wujud_produksi">${row.wujud_produksi || ''}</td>
            <td class="editable-cell" data-field="satuan_produksi" data-type="dropdown">${row.satuan_produksi || ''}</td>
            <td class="editable-cell" data-field="satuan_harga">${row.satuan_harga || ''}</td>
            <td class="editable-cell" data-field="indeks_deflator">${row.indeks_deflator || ''}</td>
            <td class="editable-cell" data-field="indeks_dbl_defl">${row.indeks_dbl_defl || ''}</td>
            <td class="editable-cell" data-field="klui_1990">${row.klui_1990 || ''}</td>
            <td class="editable-cell" data-field="kbli_2005">${row.kbli_2005 || ''}</td>
            <td class="editable-cell" data-field="kbli_2009" data-sensitive="true">${row.kbli_2009 || ''}</td>
            <td class="editable-cell" data-field="kbki_2010">${row.kbki_2010 || ''}</td>
            <td class="editable-cell" data-field="identitas">${row.identitas || ''}</td>
            <td class="editable-cell" data-field="pdrb_kbli_kode">${row.pdrb_kbli_kode || ''}</td>
            <td style="color:#64748b">${row.pdrb_kbli_uraian || ''}</td>
            <td class="editable-cell" data-field="catatan_varietas">${row.catatan_varietas || ''}</td>
            <td class="editable-cell" data-field="faktor_konversi" data-type="number">${row.faktor_konversi || 0}</td>
            <td style="text-align:center">${renderToggle(row.id, 'punya_wip', row.punya_wip)}</td>
            <td style="text-align:center">${renderToggle(row.id, 'punya_cbr', row.punya_cbr)}</td>
            <td style="text-align:center">${renderToggle(row.id, 'aktif', row.aktif)}</td>
            <td>
                <div style="display:flex; gap:4px">
                    <button class="btn btn-sm btn-primary" onclick="openDetail(${row.id})">Edit Detail</button>
                    <button class="btn btn-sm btn-ghost" onclick="showHistory(${row.id}, '${row.nama}')">Riwayat</button>
                </div>
            </td>
        </tr>
    `;
}

function renderSlotRow(row) {
    return `
        <tr class="row-slot">
            <td style="text-align:center">—</td>
            <td class="editable-cell indent-l4" data-slot="true" data-kategori="${row.kategori_kode}">${row.nama}</td>
            <td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td>
            <td>${row.pdrb_kbli_uraian}</td>
            <td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
    `;
}

function renderToggle(id, field, value) {
    return `
        <label class="mdm-toggle toggle-sm">
            <input type="checkbox" ${value ? 'checked' : ''} onchange="updateField(${id}, '${field}', this.checked)">
            <span class="mdm-toggle-track"></span>
        </label>
    `;
}

function toggleGroup(kode) {
    if (collapsedGroups.has(kode)) collapsedGroups.delete(kode);
    else collapsedGroups.add(kode);
    renderTable();
}

// ─── Inline Editing ──────────────────────────────────────────────────────────

if (tableBody) {
    tableBody.addEventListener('click', e => {
        const cell = e.target.closest('.editable-cell');
        if (!cell || currentEditing) return;
        if (cell.dataset.slot) startSlotEdit(cell);
        else startEdit(cell);
    });
}

function startEdit(cell) {
    const id = cell.parentElement.dataset.id;
    const field = cell.dataset.field;
    const type = cell.dataset.type || 'text';
    const isSensitive = cell.dataset.sensitive === 'true';
    const originalValue = cell.innerText.trim();
    currentEditing = { id, field, originalValue, element: cell, isSensitive };
    let input;
    if (field === 'satuan_produksi') {
        input = document.createElement('select');
        input.className = 'editing-input';
        input.innerHTML = satuanOptions.map(s => `<option value="${s.nama}" ${s.nama === originalValue ? 'selected' : ''}>${s.nama}</option>`).join('');
    } else {
        input = document.createElement('input');
        input.type = type === 'number' ? 'number' : 'text';
        input.className = 'editing-input';
        input.value = originalValue;
    }
    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();
    if (input.select) input.select();
    input.addEventListener('keydown', handleKeyDown);
    input.addEventListener('blur', () => finishEdit());
}

async function handleKeyDown(e) {
    if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        const saveSuccess = await finishEdit(true);
        if (saveSuccess && e.key === 'Tab') {
            const nextCell = currentEditing?.element?.nextElementSibling;
            if (nextCell && nextCell.classList.contains('editable-cell')) {
                setTimeout(() => nextCell.click(), 50);
            }
        }
    } else if (e.key === 'Escape') finishEdit(false);
}

async function finishEdit(save = false) {
    if (!currentEditing) return false;
    const { id, field, originalValue, element, isSensitive } = currentEditing;
    const input = element.querySelector('.editing-input, select');
    if (!input) return false;
    const newValue = input.value.trim();
    let success = true;
    if (save && newValue !== originalValue) {
        if (isSensitive && field === 'kbli_2009') {
            showKbliModal(id, originalValue, newValue, element);
            element.innerText = originalValue;
            currentEditing = null;
            return true;
        }
        try {
            await updateField(id, field, newValue, element);
        } catch (err) {
            element.innerText = originalValue;
            element.classList.add('cell-error');
            setTimeout(() => element.classList.remove('cell-error'), 2000);
            showToast(err.message, 'error');
            success = false;
        }
    } else element.innerText = originalValue;
    currentEditing = null;
    return success;
}

async function updateField(id, field, value, element = null) {
    const res = await fetch(`/api/master/komoditas/${id}?user_nama=Admin`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field, value })
    });
    if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Gagal menyimpan');
    }
    if (element) {
        element.innerText = value;
        element.classList.add('cell-highlight-success');
        setTimeout(() => element.classList.remove('cell-highlight-success'), 1000);
        if (field === 'satuan_produksi') {
            const hargaCell = element.parentElement.querySelector('[data-field="satuan_harga"]');
            if (hargaCell) hargaCell.innerText = `Rp/${value}`;
        }
    } else fetchData();
}

function startSlotEdit(cell) {
    const kategori = cell.dataset.kategori;
    const input = document.createElement('input');
    input.className = 'editing-input';
    input.placeholder = 'Ketik nama komoditas baru...';
    const originalText = cell.innerText;
    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();
    input.addEventListener('keydown', async e => {
        if (e.key === 'Enter') {
            const nama = input.value.trim();
            if (nama) {
                try {
                    await submitNewKomoditas(nama, kategori);
                } catch (err) {
                    showToast(err.message, 'error');
                }
            } else cell.innerText = originalText;
        } else if (e.key === 'Escape') cell.innerText = originalText;
    });
    input.addEventListener('blur', () => { if (cell.contains(input)) cell.innerText = originalText; });
}

let kbliPending = null;
function showKbliModal(id, oldVal, newVal, element) {
    kbliPending = { id, oldVal, newVal, element };
    document.getElementById('kbli-old').innerText = oldVal || '(kosong)';
    document.getElementById('kbli-new').innerText = newVal;
    document.getElementById('kbli-modal').classList.add('open');
}
function closeKbliModal() {
    document.getElementById('kbli-modal').classList.remove('open');
    kbliPending = null;
}
async function confirmKbliSave() {
    const { id, newVal, element } = kbliPending;
    const year = document.getElementById('kbli-year').value;
    const reason = document.getElementById('kbli-reason').value;
    if (!reason) { showToast('Alasan wajib diisi', 'warn'); return; }
    try {
        const res = await fetch(`/api/master/komoditas/${id}?user_nama=Admin`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ field: 'kbli_2009', value: newVal, alasan: reason, berlaku_mulai: parseInt(year) })
        });
        if (!res.ok) { const data = await res.json(); throw new Error(data.detail || 'Gagal menyimpan'); }
        element.innerText = newVal;
        element.classList.add('cell-highlight-success');
        setTimeout(() => element.classList.remove('cell-highlight-success'), 1000);
        closeKbliModal();
        showToast('KBLI diperbarui');
    } catch (err) { showToast(err.message, 'error'); }
}

function showAddPanel() { document.getElementById('add-panel').style.display = 'block'; }
function hideAddPanel() { document.getElementById('add-panel').style.display = 'none'; }

async function submitNewKomoditas(customNama = null, customKat = null) {
    const nama = customNama || document.getElementById('new-nama').value.trim();
    const kategori = customKat || document.getElementById('new-kategori').value;
    const satuan = customNama ? '' : document.getElementById('new-satuan').value;
    if (!nama) { showToast('Nama komoditas wajib diisi', 'warn'); return; }
    const res = await fetch('/api/master/komoditas?user_nama=Admin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nama, kategori_kode: kategori, satuan_produksi: satuan, aktif: true })
    });
    if (!res.ok) { const data = await res.json(); throw new Error(data.detail || 'Gagal menambah'); }
    showToast(`Berhasil menambah ${nama}`);
    if (!customNama) { document.getElementById('new-nama').value = ''; hideAddPanel(); }
    fetchData();
}

async function deleteKomoditas(id) {
    if (!confirm('Nonaktifkan komoditas ini?')) return;
    try {
        const res = await fetch(`/api/master/komoditas/${id}?user_nama=Admin`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Gagal menonaktifkan');
        showToast('Komoditas dinonaktifkan');
        fetchData();
    } catch (err) { showToast(err.message, 'error'); }
}

async function showHistory(id, nama) {
    document.getElementById('history-nama').innerText = nama;
    const list = document.getElementById('history-list');
    list.innerHTML = '<li>Memuat...</li>';
    document.getElementById('history-modal').classList.add('open');
    try {
        const res = await fetch(`/api/master/komoditas/${id}/riwayat`);
        const data = await res.json();
        if (!data.length) { list.innerHTML = '<li style="padding:20px; text-align:center; color:#94a3b8">Belum ada riwayat</li>'; return; }
        list.innerHTML = data.map(r => `
            <li class="audit-item">
                <div class="audit-dot ${r.aksi.toLowerCase()}"></div>
                <div class="audit-content">
                    <div class="audit-meta">${fmtDate(r.waktu)} — <strong>${r.user_nama}</strong></div>
                    <div class="audit-text"><span class="badge ${r.aksi === 'INSERT' ? 'badge-green' : 'badge-blue'}">${r.aksi}</span> ${r.kolom_ubah ? `Mengubah <strong>${r.kolom_ubah}</strong>` : r.aksi}</div>
                    ${r.kolom_ubah ? `<div class="audit-diff"><span class="old">${r.nilai_lama || '—'}</span> → <span class="new">${r.nilai_baru || '—'}</span></div>` : ''}
                    ${r.alasan ? `<div style="font-size:0.75rem; color:#64748b; margin-top:4px; font-style:italic">"${r.alasan}"</div>` : ''}
                </div>
            </li>
        `).join('');
    } catch (err) { list.innerHTML = `<li>Error: ${err.message}</li>`; }
}
function closeHistoryModal() { document.getElementById('history-modal').classList.remove('open'); }

// ─── Import Excel ────────────────────────────────────────────────────────────

let lastImportDiff = null;

function showImportModal() {
    document.getElementById('import-step-1').style.display = 'block';
    document.getElementById('import-step-2').style.display = 'none';
    document.getElementById('btn-apply-import').style.display = 'none';
    document.getElementById('import-modal').classList.add('open');
}

function closeImportModal() {
    document.getElementById('import-modal').classList.remove('open');
    lastImportDiff = null;
}

const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('import-file');

if (dropzone) {
    dropzone.onclick = () => fileInput.click();
    dropzone.ondragover = e => { e.preventDefault(); dropzone.classList.add('dragover'); };
    dropzone.ondragleave = () => dropzone.classList.remove('dragover');
    dropzone.ondrop = e => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    };
}
if (fileInput) fileInput.onchange = e => { if (e.target.files.length) handleFile(e.target.files[0]); };

async function handleFile(file) {
    const fd = new FormData();
    fd.append('file', file);
    try {
        const res = await fetch('/api/master/komoditas/import/preview', { method: 'POST', body: fd });
        if (!res.ok) throw new Error('Gagal memproses file Excel');
        const diff = await res.json();
        lastImportDiff = diff;
        renderImportPreview(diff);
    } catch (err) { showToast(err.message, 'error'); }
}

function renderImportPreview(diff) {
    document.getElementById('import-step-1').style.display = 'none';
    document.getElementById('import-step-2').style.display = 'block';
    document.getElementById('btn-apply-import').style.display = 'block';
    const summary = document.getElementById('import-summary');
    summary.innerHTML = `
        <div class="import-stat ok"><div class="num">${diff.unchanged.length}</div><div class="lbl">Tidak Berubah</div></div>
        <div class="import-stat changed"><div class="num">${diff.changed_detail.length}</div><div class="lbl">Berubah</div></div>
        <div class="import-stat new"><div class="num">${diff.new_detail.length}</div><div class="lbl">Baru</div></div>
        <div class="import-stat missing"><div class="num">${diff.missing_detail.length}</div><div class="lbl">Hilang</div></div>
    `;
    const tbody = document.getElementById('import-diff-body');
    tbody.innerHTML = diff.changed_detail.map((c, i) => `
        <tr>
            <td><input type="checkbox" class="import-check" data-type="changed" data-index="${i}" checked></td>
            <td><strong>${c.key}</strong></td>
            <td colspan="3">${renderDiffDetail(c.diffs)}</td>
        </tr>
    `).join('');
    document.getElementById('import-new-list').innerHTML = diff.new_detail.map((n, i) => `
        <label style="display:inline-block; margin-right:10px; background:#f0fdf4; padding:2px 8px; border-radius:4px">
            <input type="checkbox" class="import-check" data-type="new" data-index="${i}" checked> + ${n.key}
        </label>
    `).join('');
    document.getElementById('import-missing-list').innerHTML = diff.missing_detail.map((m, i) => `
        <label style="display:inline-block; margin-right:10px; background:#fff1f2; padding:2px 8px; border-radius:4px">
            <input type="checkbox" class="import-check" data-type="missing" data-index="${i}"> ─ ${m.nama}
        </label>
    `).join('');
}

function toggleAllImport(el) { document.querySelectorAll('.import-check').forEach(c => c.checked = el.checked); }

async function applyImport() {
    if (!lastImportDiff) return;
    const selectedChanged = [];
    const selectedNew = [];
    const selectedMissing = [];
    document.querySelectorAll('.import-check:checked').forEach(c => {
        const idx = parseInt(c.dataset.index);
        if (c.dataset.type === 'changed') selectedChanged.push(lastImportDiff.changed_detail[idx]);
        else if (c.dataset.type === 'new') selectedNew.push(lastImportDiff.new_detail[idx]);
        else if (c.dataset.type === 'missing') selectedMissing.push(lastImportDiff.missing_detail[idx]);
    });
    try {
        const res = await fetch('/api/master/komoditas/import/apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ diff: { changed: selectedChanged, new: selectedNew, missing: selectedMissing }, apply_new: true, apply_changed: true })
        });
        if (!res.ok) throw new Error('Gagal menerapkan import');
        const result = await res.json();
        showToast(result.message);
        closeImportModal();
        fetchData();
    } catch (err) { showToast(err.message, 'error'); }
}

// ─── Detail Drawer ───────────────────────────────────────────────────────────

let currentDetailId = null;

async function openDetail(id) {
    currentDetailId = id;
    try {
        const data = await fetch(`/api/master/komoditas/${id}`).then(r => r.json());
        document.getElementById('det-nama-header').innerText = data.nama;
        document.getElementById('det-kat-header').innerText = data.kategori_kode;
        document.getElementById('det-kode-header').innerText = data.kode_internal;
        document.getElementById('det-status-badge').innerHTML = fmtStatus(data.aktif);
        document.getElementById('det-nama').value = data.nama;
        document.getElementById('det-kategori').value = data.kategori_kode;
        document.getElementById('det-wujud').value = data.wujud_produksi || '';
        document.getElementById('det-satuan').value = data.satuan_produksi || '';
        document.getElementById('det-satuan-harga').value = data.satuan_harga || '';
        document.getElementById('det-varietas').value = data.catatan_varietas || '';
        document.getElementById('det-klui-uraian').value = data.klui_uraian || '';
        document.getElementById('det-mulai').value = data.berlaku_mulai || '';
        document.getElementById('det-sampai').value = data.berlaku_sampai || '';
        document.getElementById('det-keterangan').value = data.keterangan || '';
        document.getElementById('det-klui-1990').value = data.klui_1990 || '';
        document.getElementById('det-kbli-2005').value = data.kbli_2005 || '';
        document.getElementById('det-kbli-2009').value = data.kbli_2009 || '';
        document.getElementById('det-kbki-2010').value = data.kbki_2010 || '';
        document.getElementById('det-identitas').value = data.identitas || '';
        document.getElementById('det-pdrb-kode').value = data.pdrb_kbli_kode || '';
        document.getElementById('det-pdrb-uraian').value = data.pdrb_kbli_uraian || '';
        document.getElementById('det-deflator').value = data.indeks_deflator || '';
        document.getElementById('det-dbl-defl').value = data.indeks_dbl_defl || '';
        document.getElementById('det-konversi').value = data.faktor_konversi || '';
        document.getElementById('det-produk-jadi').value = data.produk_jadi || '';
        document.getElementById('det-punya-wip').checked = data.punya_wip;
        document.getElementById('det-punya-cbr').checked = data.punya_cbr;
        document.getElementById('det-punya-ikutan').checked = data.punya_output_ikutan;
        document.getElementById('det-metode-harga').value = data.metode_harga || 'Harga Produsen';
        updateFormulaPreview(data);
        loadDetailHistory(id);
        document.getElementById('detail-drawer-overlay').classList.add('open');
        document.getElementById('detail-drawer').classList.add('open');
        initMdmTabs('.mdm-drawer');
    } catch (err) { showToast('Gagal memuat detail: ' + err.message, 'error'); }
}

function closeDetail() {
    document.getElementById('detail-drawer-overlay').classList.remove('open');
    document.getElementById('detail-drawer').classList.remove('open');
    currentDetailId = null;
}

async function saveDetail() {
    const payload = {
        nama: document.getElementById('det-nama').value,
        kategori_kode: document.getElementById('det-kategori').value,
        wujud_produksi: document.getElementById('det-wujud').value,
        satuan_produksi: document.getElementById('det-satuan').value,
        catatan_varietas: document.getElementById('det-varietas').value,
        klui_uraian: document.getElementById('det-klui-uraian').value,
        berlaku_mulai: parseInt(document.getElementById('det-mulai').value) || null,
        berlaku_sampai: parseInt(document.getElementById('det-sampai').value) || null,
        keterangan: document.getElementById('det-keterangan').value,
        klui_1990: document.getElementById('det-klui-1990').value,
        kbli_2005: document.getElementById('det-kbli-2005').value,
        kbli_2009: document.getElementById('det-kbli-2009').value,
        kbki_2010: document.getElementById('det-kbki-2010').value,
        identitas: document.getElementById('det-identitas').value,
        pdrb_kbli_kode: document.getElementById('det-pdrb-kode').value,
        pdrb_kbli_uraian: document.getElementById('det-pdrb-uraian').value,
        indeks_deflator: document.getElementById('det-deflator').value,
        indeks_dbl_defl: document.getElementById('det-dbl-defl').value,
        faktor_konversi: parseFloat(document.getElementById('det-konversi').value) || null,
        produk_jadi: document.getElementById('det-produk-jadi').value,
        punya_wip: document.getElementById('det-punya-wip').checked,
        punya_cbr: document.getElementById('det-punya-cbr').checked,
        punya_output_ikutan: document.getElementById('det-punya-ikutan').checked,
        metode_harga: document.getElementById('det-metode-harga').value,
    };
    try {
        const res = await fetch(`/api/master/komoditas/${currentDetailId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        if (!res.ok) throw new Error('Gagal menyimpan perubahan');
        showToast('Perubahan berhasil disimpan');
        closeDetail();
        fetchData();
    } catch (err) { showToast(err.message, 'error'); }
}

async function loadDetailHistory(id) {
    const list = document.getElementById('det-history-list');
    list.innerHTML = '<li>Memuat riwayat...</li>';
    try {
        const res = await fetch(`/api/master/komoditas/${id}/riwayat`);
        const data = await res.json();
        if (!data.length) { list.innerHTML = '<li style="padding:20px; color:var(--text-muted)">Belum ada riwayat perubahan.</li>'; return; }
        list.innerHTML = data.map(r => `
            <li class="audit-item">
                <div class="audit-dot ${r.aksi.toLowerCase()}"></div>
                <div class="audit-content">
                    <div class="audit-meta">${fmtDate(r.waktu)} — ${r.user_nama}</div>
                    <div class="audit-text"><strong>${r.aksi}</strong> ${r.kolom_ubah || ''}</div>
                    <div class="audit-diff">${r.nilai_lama || '—'} → ${r.nilai_baru || '—'}</div>
                </div>
            </li>
        `).join('');
    } catch (err) {}
}

function updateFormulaPreview(data) {
    const preview = document.getElementById('det-formula-preview');
    const wipPart = data.punya_wip ? 'Output Utama × r_WIP' : '[tidak ada]';
    const ikutanPart = data.punya_output_ikutan ? 'Output Utama × r_OS' : '[tidak ada]';
    preview.innerHTML = `Output Utama = Kuantum × Harga Berlaku<br>Output Ikutan = ${ikutanPart}<br>WIP = ${wipPart}<br>Konversi = ${data.faktor_konversi ? `CPO = TBS × ${data.faktor_konversi}%` : 'tidak ada'}<br>NTB = Output Total - (Output Total × r_KA)`;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function debounce(func, wait) { let timeout; return function executedFunction(...args) { const later = () => { clearTimeout(timeout); func(...args); }; clearTimeout(timeout); timeout = setTimeout(later, wait); }; }
function showToast(msg, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${type === 'success' ? '✅' : type === 'error' ? '❌' : '⚠️'}</span> ${msg}`;
    container.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3000);
}
function exportData() { window.open('/api/master/komoditas?export=csv', '_blank'); }
