/**
 * filters.js — Shared filter state management
 * Wilayah, Tahun, Triwulan filters — persisted to sessionStorage
 */

const FILTER_KEY = 'simultan_filters';
const TAHUN_MIN = 2008;
const TAHUN_MAX = 2035;

let _state = {
  wilayah_kode: '65',
  wilayah_nama: 'Provinsi Kalimantan Utara',
  tahun: new Date().getFullYear(),
  triwulan: null,   // null = Tahunan
};

function loadFilters() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(FILTER_KEY) || '{}');
    _state = { ..._state, ...saved };
  } catch {}
}

function saveFilters() {
  sessionStorage.setItem(FILTER_KEY, JSON.stringify(_state));
}

function getFilters() { return { ..._state }; }

function setFilter(key, value) {
  _state[key] = value;
  saveFilters();
}

/** Populate select#filter-wilayah from API */
async function initWilayahFilter(selectEl, onChangeFn) {
  try {
    const list = await getWilayah();
    selectEl.innerHTML = '';
    list.forEach(w => {
      const opt = document.createElement('option');
      opt.value = w.kode;
      opt.textContent = w.nama;
      if (w.kode === _state.wilayah_kode) opt.selected = true;
      selectEl.appendChild(opt);
    });
  } catch {
    selectEl.innerHTML = '<option value="65">Prov. Kalimantan Utara</option>';
  }
  selectEl.addEventListener('change', () => {
    _state.wilayah_kode = selectEl.value;
    _state.wilayah_nama = selectEl.options[selectEl.selectedIndex].text;
    saveFilters();
    onChangeFn();
  });
}

/** Populate select#filter-tahun */
function initTahunFilter(selectEl, onChangeFn) {
  selectEl.innerHTML = '';
  for (let y = TAHUN_MAX; y >= TAHUN_MIN; y--) {
    const opt = document.createElement('option');
    opt.value = y;
    opt.textContent = y;
    if (y === _state.tahun) opt.selected = true;
    selectEl.appendChild(opt);
  }
  selectEl.addEventListener('change', () => {
    _state.tahun = parseInt(selectEl.value);
    saveFilters();
    onChangeFn();
  });
}

/** Populate select#filter-triwulan */
function initTriwulanFilter(selectEl, onChangeFn) {
  const options = [
    { value: '', label: 'Tahunan' },
    { value: '1', label: 'Triwulan I' },
    { value: '2', label: 'Triwulan II' },
    { value: '3', label: 'Triwulan III' },
    { value: '4', label: 'Triwulan IV' },
  ];
  selectEl.innerHTML = '';
  options.forEach(o => {
    const opt = document.createElement('option');
    opt.value = o.value;
    opt.textContent = o.label;
    const curVal = _state.triwulan !== null ? String(_state.triwulan) : '';
    if (o.value === curVal) opt.selected = true;
    selectEl.appendChild(opt);
  });
  selectEl.addEventListener('change', () => {
    _state.triwulan = selectEl.value === '' ? null : parseInt(selectEl.value);
    saveFilters();
    onChangeFn();
  });
}

/** Build query params for API from current filter state */
function getApiParams() {
  const f = _state;
  return {
    wilayah_kode: f.wilayah_kode,
    tahun: f.tahun,
    triwulan: f.triwulan,
  };
}

loadFilters();
