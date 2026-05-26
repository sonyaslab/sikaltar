/**
 * s3-dashboard.js — Dashboard Ringkasan PDRB
 * KPI cards, 3 Chart.js grafik, tabel triwulanan, panel kelengkapan.
 */

// ── Chart instances ────────────────────────────────────────────────────────────
let chartTren = null, chartDonut = null, chartLaju = null;

// 17 palette warna untuk kategori
const CAT_COLORS = [
  '#1B4F72','#1ABC9C','#E67E22','#9B59B6','#2ECC71',
  '#E74C3C','#3498DB','#F1C40F','#16A085','#D35400',
  '#8E44AD','#27AE60','#2980B9','#F39C12','#C0392B',
  '#1A5276','#117A65',
];

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  await initFilters();
  bindEvents();
  await loadAll();
});

async function initFilters() {
  // Wilayah
  const selW = document.getElementById('d-wilayah');
  try {
    const data = await apiFetch('/wilayah');
    selW.innerHTML = '';
    data.forEach(w => {
      const opt = document.createElement('option');
      opt.value = w.kode;
      opt.textContent = w.nama + (w.level === 'provinsi' ? ' (Provinsi)' : '');
      if (w.level === 'provinsi') opt.selected = true;
      selW.appendChild(opt);
    });
  } catch { selW.innerHTML = '<option value="65">Provinsi Kaltara</option>'; }

  // Tahun: populate 2008 to current year
  const selT = document.getElementById('d-tahun');
  const now = new Date().getFullYear();
  for (let y = now; y >= 2008; y--) {
    const opt = document.createElement('option');
    opt.value = y;
    opt.textContent = y;
    if (y === now - 1) opt.selected = true;
    selT.appendChild(opt);
  }
}

function bindEvents() {
  document.getElementById('btn-refresh').addEventListener('click', loadAll);
}

function getFilters() {
  return {
    wilayah: document.getElementById('d-wilayah').value,
    tahun:   +document.getElementById('d-tahun').value,
  };
}

// ── Load all data in parallel ─────────────────────────────────────────────────
async function loadAll() {
  const { wilayah, tahun } = getFilters();
  try {
    const [kpi, tren, dist, laju, tw, kel] = await Promise.all([
      apiFetch(`/s3/dashboard/kpi?wilayah_kode=${wilayah}&tahun=${tahun}`),
      apiFetch(`/s3/dashboard/tren?wilayah_kode=${wilayah}`),
      apiFetch(`/s3/dashboard/distribusi?wilayah_kode=${wilayah}&tahun=${tahun}`),
      apiFetch(`/s3/dashboard/laju-kategori?wilayah_kode=${wilayah}&tahun=${tahun}`),
      apiFetch(`/s3/dashboard/triwulanan?wilayah_kode=${wilayah}&tahun=${tahun}`),
      apiFetch(`/s3/dashboard/kelengkapan?tahun=${tahun}`),
    ]);
    renderKPI(kpi);
    renderTren(tren);
    renderDonut(dist, tahun);
    renderLaju(laju, tahun);
    renderTriwulanan(tw);
    renderKelengkapan(kel);
  } catch (err) {
    showToast('Gagal memuat dashboard: ' + err.message, 'error');
  }
}

// ── KPI ───────────────────────────────────────────────────────────────────────
function renderKPI(data) {
  const fmt = v => v == null ? '—' : (v / 1e6).toLocaleString('id-ID', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const fmtPct = v => v == null ? '—' : v.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '%';

  // ADHB
  document.getElementById('kpi-adhb-val').textContent = fmt(data.pdrb_adhb?.nilai) + ' T';
  renderDelta('kpi-adhb-delta', data.pdrb_adhb?.delta_pct, 'vs tahun lalu');

  // ADHK
  document.getElementById('kpi-adhk-val').textContent = fmt(data.pdrb_adhk?.nilai) + ' T';
  renderDelta('kpi-adhk-delta', data.pdrb_adhk?.delta_pct, 'vs tahun lalu');

  // Laju
  const laju = data.laju_pertumbuhan?.nilai;
  document.getElementById('kpi-laju-val').textContent = fmtPct(laju);
  const lajuSub = document.getElementById('kpi-laju-sub');
  if (laju != null) {
    lajuSub.innerHTML = `<span class="kpi-delta ${laju >= 0 ? 'up' : 'down'}">${laju >= 0 ? '▲' : '▼'} Pertumbuhan ADHK</span>`;
  }

  // Distribusi Terbesar
  const dist = data.distribusi_terbesar;
  document.getElementById('kpi-dist-val').textContent = dist?.nilai_pct != null ? fmtPct(dist.nilai_pct) : '—';
  document.getElementById('kpi-dist-nama').textContent = dist?.kategori_nama || '—';
  renderDelta('kpi-dist-delta', dist?.delta_pct, 'ppt vs tahun lalu', true);
}

function renderDelta(elId, val, label, isPp = false) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (val == null) { el.innerHTML = ''; return; }
  const dir = val >= 0 ? 'up' : 'down';
  const sign = val >= 0 ? '+' : '';
  const unit = isPp ? ' ppt' : '%';
  el.innerHTML = `<span class="kpi-delta ${dir}">${val >= 0 ? '▲' : '▼'} ${sign}${val.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${unit} ${label}</span>`;
}

// ── Grafik 1 — Tren PDRB ─────────────────────────────────────────────────────
function renderTren(data) {
  const labels = data.data.map(d => d.tahun);
  const adhb   = data.data.map(d => d.ntb_adhb);
  const adhk   = data.data.map(d => d.ntb_adhk);
  const laju   = data.data.map(d => d.laju);

  const ctx = document.getElementById('chart-tren').getContext('2d');
  if (chartTren) chartTren.destroy();

  chartTren = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'PDRB ADHB',
          data: adhb, borderColor: '#1B4F72', backgroundColor: 'rgba(27,79,114,0.08)',
          borderWidth: 2.5, pointRadius: 4, pointHoverRadius: 7, fill: true, tension: 0.3,
        },
        {
          label: 'PDRB ADHK 2010',
          data: adhk, borderColor: '#E67E22', backgroundColor: 'rgba(230,126,34,0.08)',
          borderWidth: 2.5, pointRadius: 4, pointHoverRadius: 7, fill: true, tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const v = ctx.raw;
              if (v == null) return `${ctx.dataset.label}: —`;
              return `${ctx.dataset.label}: ${(v / 1e6).toLocaleString('id-ID', { minimumFractionDigits: 2 })} Triliun Rp`;
            },
            afterBody: items => {
              const i = items[0]?.dataIndex;
              const l = laju[i];
              if (l == null) return ['Laju: — (basis)'];
              return [`Laju Pertumbuhan: ${l.toLocaleString('id-ID', { minimumFractionDigits: 2 })}%`];
            },
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        y: {
          ticks: {
            font: { size: 10 },
            callback: v => (v / 1e6).toLocaleString('id-ID', { minimumFractionDigits: 0 }) + ' T',
          },
        },
      },
    },
  });
}

// ── Grafik 2 — Donut Distribusi ───────────────────────────────────────────────
function renderDonut(data, tahun) {
  document.getElementById('donut-subtitle').textContent = `Distribusi 17 kategori — Tahun ${tahun}`;
  const labels = data.data.map(d => d.kode_singkat || d.kategori_kode);
  const values = data.data.map(d => d.distribusi_pct || 0);
  const fullNames = data.data.map(d => d.kategori_nama);

  const ctx = document.getElementById('chart-donut').getContext('2d');
  if (chartDonut) chartDonut.destroy();

  chartDonut = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: CAT_COLORS,
        borderWidth: 1, borderColor: '#fff', hoverBorderWidth: 2,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '58%',
      plugins: {
        legend: {
          position: 'right',
          labels: { boxWidth: 10, font: { size: 10 }, padding: 6 },
        },
        tooltip: {
          callbacks: {
            title: items => fullNames[items[0].dataIndex] || items[0].label,
            label: ctx => {
              const v = ctx.raw;
              const nama = fullNames[ctx.dataIndex];
              return [`${v != null ? v.toLocaleString('id-ID', { minimumFractionDigits: 2 }) : '—'}%`];
            },
          },
        },
      },
    },
  });
}

// ── Grafik 3 — Laju Pertumbuhan Bar Chart ─────────────────────────────────────
function renderLaju(data, tahun) {
  const labels = data.data.map(d => d.kode_singkat || d.kategori_kode);
  const values = data.data.map(d => d.laju_pertumbuhan_pct);
  const fullNames = data.data.map(d => d.kategori_nama);
  const colors = values.map(v => v == null ? '#ccc' : v >= 0 ? 'rgba(39,174,96,0.75)' : 'rgba(231,76,60,0.75)');
  const borders = values.map(v => v == null ? '#aaa' : v >= 0 ? '#1E8449' : '#C0392B');

  const ctx = document.getElementById('chart-laju').getContext('2d');
  if (chartLaju) chartLaju.destroy();

  chartLaju = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: `Laju Pertumbuhan ${tahun} (%)`,
        data: values,
        backgroundColor: colors, borderColor: borders, borderWidth: 1,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: items => fullNames[items[0].dataIndex],
            label: ctx => {
              const v = ctx.raw;
              return v == null ? 'Tidak ada data' : `${v.toLocaleString('id-ID', { minimumFractionDigits: 2 })}%`;
            },
          },
        },
      },
      scales: {
        x: {
          ticks: { callback: v => v + '%', font: { size: 10 } },
          grid: { color: 'rgba(0,0,0,0.05)' },
        },
        y: { ticks: { font: { size: 10 } } },
      },
    },
  });
}

// ── Tabel Triwulanan ─────────────────────────────────────────────────────────
function renderTriwulanan(data) {
  const { rows, total, tahun } = data;
  const fmtV = v => v == null ? '—' : parseFloat(v).toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmtL = v => v == null ? '—' : v.toLocaleString('id-ID', { minimumFractionDigits: 2 }) + '%';

  const allRows = [...rows, { ...total, isTot: true }];

  const el = document.getElementById('tw-container');
  el.innerHTML = `
    <table class="tw-table">
      <thead>
        <tr>
          <th>Kategori</th>
          <th>TW I</th><th>TW II</th><th>TW III</th><th>TW IV</th>
          <th>Tahunan</th><th>Laju (%)</th>
        </tr>
      </thead>
      <tbody>
        ${allRows.map(r => {
          const isT = r.isTot;
          const laju = r.laju_pertumbuhan_pct;
          const lCls = laju != null ? (laju < 0 ? 'laju-neg' : 'laju-pos') : '';
          return `<tr class="${isT ? 'tw-total' : ''}">
            <td>${isT ? '<strong>PDRB</strong>' : (r.kode_singkat ? `<b>${r.kode_singkat}</b> — ` : '') + r.kategori_nama}</td>
            <td>${fmtV(r.tw1_adhk)}</td><td>${fmtV(r.tw2_adhk)}</td>
            <td>${fmtV(r.tw3_adhk)}</td><td>${fmtV(r.tw4_adhk)}</td>
            <td>${fmtV(r.tahunan_adhk)}</td>
            <td class="${lCls}">${fmtL(laju)}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

// ── Kelengkapan Panel ────────────────────────────────────────────────────────
function renderKelengkapan(data) {
  document.getElementById('kel-title').textContent = `Progress Input Data — Tahun ${data.tahun}`;
  const el = document.getElementById('kel-container');
  if (!data.wilayah || data.wilayah.length === 0) {
    el.innerHTML = '<div class="kel-loading">Tidak ada data wilayah</div>';
    return;
  }
  el.innerHTML = data.wilayah.map(w => {
    const pct = w.pct || 0;
    const fillClass = pct >= 100 ? 'done' : pct < 40 ? 'low' : 'mid';
    const check = pct >= 100 ? ' ✓' : '';
    const label = w.level === 'kabupaten' ? 'Kab. ' : 'Kota ';
    return `
      <div class="kel-item">
        <div class="kel-nama" title="${w.wilayah_nama}">${label}${w.wilayah_nama.replace(/^Kabupaten |^Kota /i, '')}</div>
        <div class="kel-bar-wrap">
          <div class="kel-bar-fill ${fillClass}" style="width:${Math.min(pct, 100)}%"></div>
        </div>
        <div class="kel-pct" style="color:${pct >= 100 ? 'var(--success)' : pct < 40 ? 'var(--danger)' : 'var(--warn)'}">${pct}%</div>
        <div class="kel-check">${check}</div>
      </div>`;
  }).join('');
}

// ── Toast ──────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  document.getElementById('toast-container').appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
