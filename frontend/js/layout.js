/**
 * layout.js — SIKALTARA Layout Manager
 * Role-based sidebar + admin route guard + mobile collapse.
 * Depends on: auth.js (harus di-load lebih dulu)
 *
 * Usage: <script>LAYOUT.init();</script>
 *   atau: LAYOUT.init({ pageId: 'dashboard', adminOnly: false })
 */

const LAYOUT = (() => {

  // ── Registry halaman ──────────────────────────────────────────────────────
  const PAGE_REGISTRY = {
    'index.html':               { id: 'dashboard',       adminOnly: false },
    '':                         { id: 'dashboard',       adminOnly: false },
    's1-harga.html':            { id: 's1-harga',        adminOnly: false },
    's1-produksi.html':         { id: 's1-produksi',     adminOnly: false },
    's1-rasio.html':            { id: 's1-rasio',        adminOnly: true  },
    's1-deflator.html':         { id: 's1-deflator',     adminOnly: false },
    's2-lk.html':               { id: 's2-lk',           adminOnly: false },
    's3-dashboard.html':        { id: 's3-dashboard',    adminOnly: true  },
    's3-tabel.html':            { id: 's3-tabel',        adminOnly: true  },
    'mdm-index.html':           { id: 'mdm-index',       adminOnly: true  },
    'mdm-komoditas-master.html':{ id: 'mdm-komoditas',   adminOnly: true  },
    'mdm-kategori.html':        { id: 'mdm-kategori',    adminOnly: true  },
    'mdm-klasifikasi.html':     { id: 'mdm-klasifikasi', adminOnly: true  },
    'mdm-satuan.html':          { id: 'mdm-satuan',      adminOnly: true  },
    'mdm-metode.html':          { id: 'mdm-metode',      adminOnly: true  },
    'mdm-faktor-konversi.html': { id: 'mdm-faktor',      adminOnly: true  },
    'mdm-audit.html':           { id: 'mdm-audit',       adminOnly: true  },
    'admin-users.html':         { id: 'mdm-users',       adminOnly: true  },
    'admin-rasio.html':         { id: 'admin-rasio',     adminOnly: true  },
    'admin-riwayat.html':       { id: 'admin-riwayat',   adminOnly: true  },
  };

  // ── Definisi Menu ──────────────────────────────────────────────────────────
  const MENU_OPERATOR = [
    { type: 'link',      id: 'dashboard',  icon: '📊', label: 'Dashboard',         href: 'index.html' },
    { type: 'separator' },
    { type: 'group', id: 's1', icon: '📥', label: 'Input Data', children: [
      { id: 's1-harga',    icon: '💰', label: 'Harga (S1.H)',           href: 's1-harga.html' },
      { id: 's1-produksi', icon: '🌾', label: 'Produksi (S1.P)',        href: 's1-produksi.html' },
      { id: 's1-deflator', icon: '📉', label: 'Indeks Deflator (S1.I)', href: 's1-deflator.html' },
    ]},
    { type: 'group', id: 's2', icon: '📋', label: 'Lembar Kerja (S2)', children: [
      { id: 's2-lk',    icon: '📄', label: 'Lihat per Kategori', href: 's2-lk.html' },
      { id: 's2-rekap', icon: '📊', label: 'Rekap Triwulan',     href: 's2-lk.html#rekap' },
    ]},
    { type: 'separator' },
    { type: 'link', id: 'profile', icon: '👤', label: 'Profil Saya', href: 'profile.html' },
  ];

  const MENU_ADMIN = [
    { type: 'link',      id: 'dashboard',  icon: '📊', label: 'Dashboard',         href: 'index.html' },
    { type: 'separator' },
    { type: 'group', id: 's1', icon: '📥', label: 'Input Data', children: [
      { id: 's1-harga',    icon: '💰', label: 'Harga (S1.H)',           href: 's1-harga.html' },
      { id: 's1-produksi', icon: '🌾', label: 'Produksi (S1.P)',        href: 's1-produksi.html' },
      { id: 's1-rasio',    icon: '📈', label: 'Rasio (S1.R)',           href: 's1-rasio.html' },
      { id: 's1-deflator', icon: '📉', label: 'Indeks Deflator (S1.I)', href: 's1-deflator.html' },
      { id: 's1-adj',      icon: '⚙️',  label: 'Adjustment (S1.ADJ)',   href: '#', badge: 'soon' },
    ]},
    { type: 'group', id: 's2', icon: '📋', label: 'Lembar Kerja (S2)', children: [
      { id: 's2-lk',    icon: '📄', label: 'Lihat per Kategori', href: 's2-lk.html' },
      { id: 's2-rekap', icon: '📊', label: 'Rekap Triwulan',     href: 's2-lk.html#rekap' },
    ]},
    { type: 'group', id: 's3', icon: '📈', label: 'Tabel Pokok (S3)', children: [
      { id: 's3-dashboard', icon: '📊', label: 'Dashboard Ringkasan', href: 's3-dashboard.html' },
      { id: 's3-tabel',     icon: '📋', label: 'Tabel Pokok BPS',     href: 's3-tabel.html' },
    ]},
    { type: 'separator' },
    { type: 'group', id: 'admin-menu', icon: '⚙️', label: 'ADMIN', adminOnly: true, children: [
      { id: 'mdm-komoditas',   icon: '🌾', label: 'Master Komoditas',    href: 'mdm-komoditas-master.html' },
      { id: 'mdm-kategori',    icon: '📂', label: 'Master Kategori',     href: 'mdm-kategori.html' },
      { id: 'admin-rasio',     icon: '📊', label: 'Rasio Referensi',     href: 'admin-rasio.html' },
      { id: 'mdm-users',       icon: '👥', label: 'Manajemen User',      href: 'admin-users.html' },
      { id: 'admin-riwayat',   icon: '📜', label: 'Riwayat Perubahan',   href: 'admin-riwayat.html' },
    ]},
    { type: 'separator' },
    { type: 'link', id: 'profile', icon: '👤', label: 'Profil Saya', href: 'profile.html' },
  ];

  // ── Deteksi halaman saat ini ───────────────────────────────────────────────
  function _detectPage() {
    const filename = window.location.pathname.split('/').pop() || 'index.html';
    return PAGE_REGISTRY[filename] || { id: filename.replace('.html', ''), adminOnly: false };
  }

  // ── Set semua group yang mengandung halaman aktif jadi open ───────────────
  function _getOpenGroups(activeId, menu) {
    const open = new Set();
    menu.forEach(item => {
      if (item.type === 'group' && item.children) {
        if (item.children.some(c => c.id === activeId)) {
          open.add(item.id);
        }
      }
    });
    return open;
  }

  // ── Render sidebar HTML ────────────────────────────────────────────────────
  function _renderSidebar(activeId) {
    const isAdmin = AUTH.isAdmin();
    const menu    = isAdmin ? MENU_ADMIN : MENU_OPERATOR;
    const openGroups = _getOpenGroups(activeId, menu);
    const role    = AUTH.getRole();
    const wilayah = AUTH.getWilayahKode();

    const wilayahBadge = (!isAdmin && wilayah)
      ? `<div class="sb-wilayah-badge">📍 Wilayah: ${wilayah}</div>`
      : '';

    let html = `
      <div class="sb-brand">
        <div class="sb-logo">
          <span class="sb-logo-icon">📊</span>
          <div>
            <div class="sb-app-name">SIKALTARA</div>
            <div class="sb-app-sub">LK PDRB Kalimantan Utara</div>
          </div>
        </div>
        ${wilayahBadge}
      </div>
      <nav class="sb-nav" id="sb-nav-items">
    `;

    menu.forEach(item => {
      if (item.type === 'separator') {
        html += `<div class="sb-separator"></div>`;
        return;
      }

      if (item.type === 'link') {
        const active = item.id === activeId ? ' active' : '';
        const soon   = item.badge === 'soon' ? ' sb-item-soon' : '';
        html += `
          <a href="${item.href}" class="sb-item${active}${soon}" data-id="${item.id}">
            <span class="sb-icon">${item.icon}</span>
            <span class="sb-label">${item.label}</span>
            ${item.badge && item.badge !== 'soon' ? `<span class="sb-badge">${item.badge}</span>` : ''}
          </a>
        `;
        return;
      }

      if (item.type === 'group') {
        const isOpen    = openGroups.has(item.id);
        const hasActive = item.children && item.children.some(c => c.id === activeId);
        const openClass = isOpen ? ' open' : '';
        const activeClass = hasActive ? ' has-active' : '';

        html += `
          <div class="sb-group${openClass}${activeClass}" data-group="${item.id}">
            <button class="sb-group-toggle" onclick="LAYOUT.toggleGroup('${item.id}')">
              <span class="sb-icon">${item.icon}</span>
              <span class="sb-label">${item.label}</span>
              <span class="sb-chevron">›</span>
            </button>
            <div class="sb-group-children">
        `;

        if (item.children) {
          item.children.forEach(child => {
            const childActive = child.id === activeId ? ' active' : '';
            const childSoon   = child.badge === 'soon' ? ' sb-item-soon' : '';
            html += `
              <a href="${child.href}" class="sb-child${childActive}${childSoon}" data-id="${child.id}">
                <span class="sb-child-icon">${child.icon}</span>
                <span class="sb-label">${child.label}</span>
                ${child.badge && child.badge !== 'soon' ? `<span class="sb-badge">${child.badge}</span>` : ''}
              </a>
            `;
          });
        }

        html += `</div></div>`;
      }
    });

    html += `</nav>`;

    // Tombol collapse di bawah sidebar
    html += `
      <button class="sb-collapse-btn" id="sb-collapse-btn" onclick="LAYOUT.toggleCollapse()" title="Sembunyikan/tampilkan sidebar">
        <span class="sb-collapse-icon">◀</span>
      </button>
    `;

    // Cari atau buat elemen sidebar
    let sidebar = document.querySelector('.sidebar, .mdm-sidebar, .cat-sidebar');
    if (sidebar) {
      // Tambahkan class baru ke sidebar yang ada
      sidebar.className = 'sb-sidebar';
      sidebar.id = 'app-sidebar';
      sidebar.innerHTML = html;
    } else {
      // Buat sidebar baru dan inject ke awal .app-shell / body
      sidebar = document.createElement('aside');
      sidebar.className = 'sb-sidebar';
      sidebar.id = 'app-sidebar';
      sidebar.innerHTML = html;
      const shell = document.querySelector('.app-shell, .mdm-shell, .lk-shell, body');
      if (shell) shell.prepend(sidebar);
    }

    // Sesuaikan main content margin
    _adjustMainContent();
  }

  function _adjustMainContent() {
    const main = document.querySelector('.main-content, .mdm-main, .lk-main');
    if (main) {
      main.style.marginLeft = 'var(--sb-width, 240px)';
      main.style.transition = 'margin-left 250ms ease';
    }
  }

  // ── Mobile collapse setup ─────────────────────────────────────────────────
  function _setupCollapse() {
    // Restore state dari localStorage
    const collapsed = localStorage.getItem('sb_collapsed') === '1';
    if (collapsed) _applyCollapsed(true, false);

    // Auto-collapse di mobile
    if (window.innerWidth < 768) {
      _applyCollapsed(true, false);
    }

    // Mobile overlay click to close
    let overlay = document.getElementById('sb-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'sb-overlay';
      overlay.className = 'sb-overlay';
      overlay.onclick = () => LAYOUT.toggleCollapse();
      document.body.appendChild(overlay);
    }

    // Hamburger button untuk mobile
    _injectMobileToggle();

    window.addEventListener('resize', () => {
      if (window.innerWidth < 768) {
        _applyCollapsed(true, false);
      }
    });
  }

  function _injectMobileToggle() {
    const header = document.querySelector('.page-header, .mdm-topbar, .lk-header');
    if (!header || document.getElementById('sb-hamburger')) return;
    const btn = document.createElement('button');
    btn.id = 'sb-hamburger';
    btn.className = 'sb-hamburger';
    btn.onclick = () => LAYOUT.toggleCollapse();
    btn.innerHTML = '☰';
    btn.title = 'Menu';
    header.prepend(btn);
  }

  function _applyCollapsed(collapsed, save = true) {
    const sidebar = document.getElementById('app-sidebar');
    const main    = document.querySelector('.main-content, .mdm-main, .lk-main');
    const btn     = document.getElementById('sb-collapse-btn');
    const overlay = document.getElementById('sb-overlay');

    if (!sidebar) return;

    if (collapsed) {
      sidebar.classList.add('sb-collapsed');
      if (main) main.style.marginLeft = 'var(--sb-collapsed-width, 60px)';
      if (btn)  btn.querySelector('.sb-collapse-icon').textContent = '▶';
      if (overlay && window.innerWidth < 768) overlay.classList.add('active');
    } else {
      sidebar.classList.remove('sb-collapsed');
      if (main) main.style.marginLeft = 'var(--sb-width, 240px)';
      if (btn)  btn.querySelector('.sb-collapse-icon').textContent = '◀';
      if (overlay) overlay.classList.remove('active');
    }

    if (save) localStorage.setItem('sb_collapsed', collapsed ? '1' : '0');
  }

  // ── Admin guard ───────────────────────────────────────────────────────────
  function _adminGuard() {
    if (!AUTH.isAdmin()) {
      // Tampilkan toast kemudian redirect
      _showToast('Akses ditolak. Fitur ini hanya untuk Admin.', 'error');
      setTimeout(() => { window.location.href = 'index.html'; }, 1800);
      return false;
    }
    return true;
  }

  // ── Toast (fallback jika belum ada) ───────────────────────────────────────
  function _showToast(msg, type = 'info') {
    // Coba pakai fungsi global jika ada
    if (typeof showToast === 'function') { showToast(msg, type); return; }

    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    container.appendChild(t);
    setTimeout(() => t.remove(), 4000);
  }

  // ── Admin Sub-Sidebar ─────────────────────────────────────────────────────

  const ADMIN_SUBNAV = [
    { id: 'mdm-komoditas',  icon: '🌾', label: 'Master Komoditas', href: 'mdm-komoditas-master.html', countUrl: '/api/mdm/komoditas?limit=1' },
    { id: 'mdm-kategori',   icon: '📂', label: 'Master Kategori',  href: 'mdm-kategori.html',          countUrl: null },
    { id: 'admin-rasio',    icon: '📊', label: 'Rasio Referensi',  href: 'admin-rasio.html',            countUrl: null },
    { id: 'mdm-users',      icon: '👥', label: 'Manajemen User',   href: 'admin-users.html',            countUrl: '/admin/users' },
    { id: 'admin-riwayat',  icon: '📜', label: 'Riwayat Perubahan',href: 'admin-riwayat.html',          countUrl: null },
  ];

  function _renderAdminSubSidebar(activeId) {
    const main = document.querySelector('.mdm-main, .main-content, .lk-main');
    if (!main || document.getElementById('admin-subnav')) return;

    const nav = document.createElement('aside');
    nav.id = 'admin-subnav';
    nav.className = 'admin-subnav';

    nav.innerHTML = `
      <div class="asn-header">
        <span class="asn-title">⚙️ Admin</span>
        <button class="asn-toggle" onclick="LAYOUT.toggleAdminSubnav()" title="Sembunyikan">◀</button>
      </div>
      <nav class="asn-nav">
        ${ADMIN_SUBNAV.map(item => `
          <a href="${item.href}" class="asn-item${item.id === activeId ? ' active' : ''}" data-asn-id="${item.id}">
            <span class="asn-icon">${item.icon}</span>
            <span class="asn-label">${item.label}</span>
            <span class="asn-count" id="asnc-${item.id}"></span>
          </a>`).join('')}
      </nav>
    `;

    main.prepend(nav);
    main.style.display = 'flex';
    main.style.flexDirection = 'row';
    main.style.alignItems = 'stretch';

    // Wrap existing content
    const children = Array.from(main.children).filter(el => el.id !== 'admin-subnav');
    const wrapper = document.createElement('div');
    wrapper.className = 'admin-content-wrap';
    children.forEach(el => wrapper.appendChild(el));
    main.appendChild(wrapper);

    // Load badge counts async
    _loadSubnavCounts();

    // Restore collapsed state
    if (localStorage.getItem('asn_collapsed') === '1') _applyAsnCollapsed(true, false);
  }

  async function _loadSubnavCounts() {
    const token = localStorage.getItem('sikaltar_token');
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

    for (const item of ADMIN_SUBNAV) {
      if (!item.countUrl) continue;
      try {
        const res = await fetch(item.countUrl, { headers });
        if (!res.ok) continue;
        const data = await res.json();
        const el = document.getElementById(`asnc-${item.id}`);
        if (!el) continue;
        // Heuristic: cari angka dari response
        const count = data.total ?? data.count ?? (Array.isArray(data.users) ? data.total : null)
          ?? (Array.isArray(data) ? data.length : null);
        if (count != null) el.textContent = count;
      } catch {/* ignore */}
    }
  }

  function _applyAsnCollapsed(collapsed, save = true) {
    const nav = document.getElementById('admin-subnav');
    const btn = nav ? nav.querySelector('.asn-toggle') : null;
    if (!nav) return;
    if (collapsed) {
      nav.classList.add('asn-collapsed');
      if (btn) btn.textContent = '▶';
    } else {
      nav.classList.remove('asn-collapsed');
      if (btn) btn.textContent = '◀';
    }
    if (save) localStorage.setItem('asn_collapsed', collapsed ? '1' : '0');
  }

  function toggleAdminSubnav() {
    const nav = document.getElementById('admin-subnav');
    if (!nav) return;
    _applyAsnCollapsed(!nav.classList.contains('asn-collapsed'));
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  function init(options = {}) {
    if (!AUTH.isLoggedIn()) { AUTH.logout(); return; }

    const pageConfig = _detectPage();
    const pageId     = options.pageId    ?? pageConfig.id;
    const adminOnly  = options.adminOnly ?? pageConfig.adminOnly;

    if (adminOnly && !_adminGuard()) return;

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        _renderSidebar(pageId);
        _setupCollapse();
        if (adminOnly) _renderAdminSubSidebar(pageId);
      });
    } else {
      _renderSidebar(pageId);
      _setupCollapse();
      if (adminOnly) _renderAdminSubSidebar(pageId);
    }
  }

  /** Toggle collapse sidebar */
  function toggleCollapse() {
    const sidebar = document.getElementById('app-sidebar');
    if (!sidebar) return;
    const isCollapsed = sidebar.classList.contains('sb-collapsed');
    _applyCollapsed(!isCollapsed);
  }

  /** Toggle expand/collapse group item */
  function toggleGroup(groupId) {
    const group = document.querySelector(`[data-group="${groupId}"]`);
    if (!group) return;
    group.classList.toggle('open');
  }

  /** requireAdmin() — gunakan di halaman admin */
  function requireAdmin() {
    if (!AUTH.isLoggedIn()) { AUTH.logout(); return false; }
    return _adminGuard();
  }

  return { init, toggleCollapse, toggleGroup, toggleAdminSubnav, requireAdmin };

})();
