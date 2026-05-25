/**
 * s2-sidebar.js — Category Navigation Sidebar for S2
 *
 * Fitur:
 *  - Pohon kategori hierarkis dengan status kelengkapan
 *  - Badge: ✓ Lengkap / ⚠ Parsial / ○ Kosong
 *  - Progress fraction per item (terisi/total)
 *  - Collapse/expand level 1 → tampilkan level 2 → klik level 3 untuk load worksheet
 */

const _collapsedKeys = new Set();   // kode level 1 yang di-collapse

/**
 * Build sidebar category tree dari data status.
 * @param {Object} statusData  - Map kode → {kode, nama, level, parent_kode, status, terisi, total_komoditas}
 * @param {string} activeKode  - Kode yang sedang aktif
 * @param {function} onSelect  - Callback (kode) ketika item dipilih
 */
function buildCatTree(statusData, activeKode, onSelect) {
  const container = document.getElementById('cat-nav-container');
  if (!container) return;
  container.innerHTML = '';

  const byLevel = { 1: [], 2: [], 3: [] };
  Object.values(statusData).forEach(item => {
    if (byLevel[item.level]) byLevel[item.level].push(item);
  });

  // Sort by urutan
  [1, 2, 3].forEach(l => byLevel[l].sort((a, b) => a.urutan - b.urutan));

  // Build level 1
  byLevel[1].forEach(l1 => {
    // Aggregate status dari children
    const children2 = byLevel[2].filter(x => x.parent_kode === l1.kode);
    const allStatus = children2.flatMap(c2 => {
      const children3 = byLevel[3].filter(x => x.parent_kode === c2.kode);
      return children3.length ? children3 : [c2];
    });
    const totalTerisi = allStatus.reduce((a, x) => a + (x.terisi || 0), 0);
    const totalKom    = allStatus.reduce((a, x) => a + (x.total_komoditas || 0), 0);
    const aggrStatus  = totalKom === 0 ? 'kosong'
      : totalTerisi === totalKom ? 'lengkap'
      : totalTerisi > 0 ? 'parsial'
      : 'kosong';

    const isCollapsed = _collapsedKeys.has(l1.kode);
    const l1El = _makeItem(l1.kode, l1.nama, 1, aggrStatus, totalTerisi, totalKom,
      false, () => {
        // Toggle collapse
        if (_collapsedKeys.has(l1.kode)) _collapsedKeys.delete(l1.kode);
        else _collapsedKeys.add(l1.kode);
        buildCatTree(statusData, activeKode, onSelect);
      }
    );
    l1El.querySelector('.cat-toggle').textContent = isCollapsed ? '▶' : '▼';
    container.appendChild(l1El);

    if (!isCollapsed) {
      // Level 2
      children2.forEach(l2 => {
        const children3 = byLevel[3].filter(x => x.parent_kode === l2.kode);
        const terisi2 = children3.reduce((a, x) => a + x.terisi, 0) || l2.terisi;
        const total2  = children3.reduce((a, x) => a + x.total_komoditas, 0) || l2.total_komoditas;
        const st2     = total2 === 0 ? 'kosong' : terisi2 === total2 ? 'lengkap' : terisi2 > 0 ? 'parsial' : 'kosong';

        const l2El = _makeItem(l2.kode, l2.nama, 2, st2, terisi2, total2,
          l2.kode === activeKode,
          () => {
            // Level 2 bisa di-klik untuk load worksheet (jika punya komoditas langsung)
            if (l2.total_komoditas > 0) onSelect(l2.kode);
          }
        );
        container.appendChild(l2El);

        // Level 3
        children3.forEach(l3 => {
          const l3El = _makeItem(l3.kode, l3.nama, 3, l3.status, l3.terisi, l3.total_komoditas,
            l3.kode === activeKode,
            () => onSelect(l3.kode)
          );
          container.appendChild(l3El);
        });
      });
    }
  });
}

function _makeItem(kode, nama, level, status, terisi, total, isActive, onClick) {
  const el = document.createElement('div');
  el.className = `cat-tree-item${isActive ? ' active' : ''}`;
  el.dataset.level = level;
  el.dataset.kode = kode;

  const statusIcon = status === 'lengkap' ? '✓'
    : status === 'parsial' ? '⚠'
    : '○';
  const progressTxt = total > 0 ? `${terisi}/${total}` : '';
  const toggleSpan  = level === 1 ? '<span class="cat-toggle" style="font-size:0.7rem;margin-right:2px;opacity:0.5">▼</span>' : '';

  el.innerHTML = `
    ${toggleSpan}
    <span class="status-dot ${status}"></span>
    <span class="cat-name">
      <span class="cat-code">${kode}</span>${nama}
    </span>
    ${total > 0 ? `<span class="cat-progress">${progressTxt}</span>` : ''}
  `;

  el.addEventListener('click', (e) => {
    e.stopPropagation();
    onClick();
  });
  return el;
}


/**
 * Update semua status dot setelah cascade refresh tanpa rebuild seluruh tree.
 */
function updateCatStatuses(statusData) {
  Object.values(statusData).forEach(item => {
    const el = document.querySelector(`.cat-tree-item[data-kode="${item.kode}"] .status-dot`);
    if (el) {
      el.className = `status-dot ${item.status}`;
    }
    const prog = document.querySelector(`.cat-tree-item[data-kode="${item.kode}"] .cat-progress`);
    if (prog && item.total_komoditas > 0) {
      prog.textContent = `${item.terisi}/${item.total_komoditas}`;
    }
  });
}
