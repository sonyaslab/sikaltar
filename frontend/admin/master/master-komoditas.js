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
        if (sel) sel.innerHTML = data.map(s => `<option value="${s.nama}">${s.nama}</option>`).join('');
    } catch (err) {}
}

async function loadKategori() {
    try {
        const data = await mdmGetKategori();
        kategoriOptions = data;
        const filterSel = document.getElementById('filter-kategori');
        const addSel = document.getElementById('new-kategori');

        const opts = data.map(k => `<option value="${k.kode}">${k.kode} ${k.nama}</option>`).join('');
        if (filterSel) filterSel.innerHTML += opts;
        if (addSel) addSel.innerHTML = opts;
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
                    <button class="btn btn-sm btn-ghost" onclick="showHistory(${row.id}, '${row.nama}')">Riwayat</button>
                    <button class="btn btn-sm btn-danger-ghost" onclick="deleteKomoditas(${row.id})">🗑️</button>
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
