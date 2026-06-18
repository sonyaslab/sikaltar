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
    'index.html':               { id: 'dashboard',       adminOnly: false, showAdminSubnav: false },
    '':                         { id: 'dashboard',       adminOnly: false, showAdminSubnav: false },
    's1-harga.html':            { id: 's1-harga',        adminOnly: false, showAdminSubnav: false },
    's1-produksi.html':         { id: 's1-produksi',     adminOnly: false, showAdminSubnav: false },
    's1-rasio.html':            { id: 's1-rasio',        adminOnly: false, showAdminSubnav: false },
    's1-deflator.html':         { id: 's1-deflator',     adminOnly: false, showAdminSubnav: false },
    's2-lk.html':               { id: 's2-lk',           adminOnly: false, showAdminSubnav: false },
    's3-dashboard.html':        { id: 's3-dashboard',    adminOnly: false, showAdminSubnav: false },
    's3-tabel.html':            { id: 's3-tabel',        adminOnly: false, showAdminSubnav: false },
    'mdm-index.html':           { id: 'mdm-index',       adminOnly: true,  showAdminSubnav: true },
    'mdm-komoditas-master.html':{ id: 'mdm-komoditas',   adminOnly: true,  showAdminSubnav: true },
    'mdm-kategori.html':        { id: 'mdm-kategori',    adminOnly: true,  showAdminSubnav: true },
    'mdm-klasifikasi.html':     { id: 'mdm-klasifikasi', adminOnly: true,  showAdminSubnav: true },
    'mdm-satuan.html':          { id: 'mdm-satuan',      adminOnly: true,  showAdminSubnav: true },
    'mdm-metode.html':          { id: 'mdm-metode',      adminOnly: true,  showAdminSubnav: true },
    'mdm-faktor-konversi.html': { id: 'mdm-faktor',      adminOnly: true,  showAdminSubnav: true },
    'mdm-audit.html':           { id: 'mdm-audit',       adminOnly: true,  showAdminSubnav: true },
    'admin-users.html':         { id: 'mdm-users',       adminOnly: true,  showAdminSubnav: true },
    'admin-rasio.html':         { id: 'admin-rasio',     adminOnly: true,  showAdminSubnav: true },
    'admin-riwayat.html':       { id: 'admin-riwayat',   adminOnly: true,  showAdminSubnav: true },
  };

  // ── SVG Icons (menggantikan emoji) ────────────────────────────────────────
  const SVG_ICONS = {
    dashboard:   '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>',
    input:       '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>',
    harga:       '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>',
    produksi:    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>',
    rasio:       '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>',
    deflator:    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline><polyline points="17 18 23 18 23 12"></polyline></svg>',
    lembar:      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>',
    tabel:       '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11H3v10h6V11zM21 3h-6v18h6V3zM15 7H9v14h6V7z"></path></svg>',
    admin:       '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>',
    komoditas:   '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>',
    kategori:    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>',
    users:       '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>',
    riwayat:     '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>',
    profile:     '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
    logo:        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>',
    chevron:     '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>',
    collapse:    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>',
    hamburger:   '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>',
  };

  // ── Definisi Menu (Operator) ──────────────────────────────────────────────
  const MENU_OPERATOR = [
    { type: 'link', id: 'dashboard', icon: SVG_ICONS.dashboard, label: 'Dashboard', href: 'index.html' },
    { type: 'separator' },
    { type: 'group', id: 's1', icon: SVG_ICONS.input, label: 'Input Data', children: [
      { id: 's1-harga',    icon: SVG_ICONS.harga,    label: 'Harga (S1.H)',           href: 's1-harga.html' },
      { id: 's1-produksi', icon: SVG_ICONS.produksi, label: 'Produksi (S1.P)',        href: 's1-produksi.html' },
      { id: 's1-deflator', icon: SVG_ICONS.deflator, label: 'Indeks Deflator (S1.I)', href: 's1-deflator.html' },
    ]},
    { type: 'group', id: 's2', icon: SVG_ICONS.lembar, label: 'Lembar Kerja (S2)', children: [
      { id: 's2-lk',    icon: SVG_ICONS.lembar, label: 'Lihat per Kategori', href: 's2-lk.html' },
      { id: 's2-rekap', icon: SVG_ICONS.tabel,  label: 'Rekap Triwulan',     href: 's2-lk.html#rekap' },
    ]},
    { type: 'separator' },
    { type: 'link', id: 'profile', icon: SVG_ICONS.profile, label: 'Profil Saya', href: 'profile.html' },
  ];

  // ── Definisi Menu (Admin) ─────────────────────────────────────────────────
  const MENU_ADMIN = [
    { type: 'link', id: 'dashboard', icon: SVG_ICONS.dashboard, label: 'Dashboard', href: 'index.html' },
    { type: 'separator' },
    { type: 'group', id: 's1', icon: SVG_ICONS.input, label: 'Input Data', children: [
      { id: 's1-harga',    icon: SVG_ICONS.harga,    label: 'Harga (S1.H)',           href: 's1-harga.html' },
      { id: 's1-produksi', icon: SVG_ICONS.produksi, label: 'Produksi (S1.P)',        href: 's1-produksi.html' },
      { id: 's1-rasio',    icon: SVG_ICONS.rasio,    label: 'Rasio (S1.R)',           href: 's1-rasio.html' },
      { id: 's1-deflator', icon: SVG_ICONS.deflator, label: 'Indeks Deflator (S1.I)', href: 's1-deflator.html' },
    ]},
    { type: 'group', id: 's2', icon: SVG_ICONS.lembar, label: 'Lembar Kerja (S2)', children: [
      { id: 's2-lk',    icon: SVG_ICONS.lembar, label: 'Lihat per Kategori', href: 's2-lk.html' },
      { id: 's2-rekap', icon: SVG_ICONS.tabel,  label: 'Rekap Triwulan',     href: 's2-lk.html#rekap' },
    ]},
    { type: 'group', id: 's3', icon: SVG_ICONS.tabel, label: 'Tabel Pokok (S3)', children: [
      { id: 's3-dashboard', icon: SVG_ICONS.dashboard, label: 'Dashboard Ringkasan', href: 's3-dashboard.html' },
      { id: 's3-tabel',     icon: SVG_ICONS.tabel,     label: 'Tabel Pokok BPS',     href: 's3-tabel.html' },
    ]},
    { type: 'separator' },
    { type: 'group', id: 'admin-menu', icon: SVG_ICONS.admin, label: 'ADMIN', adminOnly: true, children: [
      { id: 'mdm-komoditas', icon: SVG_ICONS.komoditas, label: 'Master Komoditas',  href: 'mdm-komoditas-master.html' },
      { id: 'mdm-kategori',  icon: SVG_ICONS.kategori,  label: 'Master Kategori',   href: 'mdm-kategori.html' },
      { id: 'admin-rasio',   icon: SVG_ICONS.rasio,     label: 'Rasio Referensi',   href: 'admin-rasio.html' },
      { id: 'mdm-users',     icon: SVG_ICONS.users,     label: 'Manajemen User',    href: 'admin-users.html' },
      { id: 'admin-riwayat', icon: SVG_ICONS.riwayat,   label: 'Riwayat Perubahan', href: 'admin-riwayat.html' },
    ]},
    { type: 'separator' },
    { type: 'link', id: 'profile', icon: SVG_ICONS.profile, label: 'Profil Saya', href: 'profile.html' },
  ];

  // ── Admin Sub-Sidebar (hanya untuk master data admin) ─────────────────────
  const ADMIN_SUBNAV = [
    { id: 'mdm-komoditas',  icon: SVG_ICONS.komoditas, label: 'Master Komoditas', href: 'mdm-komoditas-master.html', countUrl: '/api/mdm/komoditas?limit=1' },
    { id: 'mdm-kategori',   icon: SVG_ICONS.kategori,  label: 'Master Kategori',  href: 'mdm-kategori.html',          countUrl: null },
    { id: 'admin-rasio',    icon: SVG_ICONS.rasio,     label: 'Rasio Referensi',  href: 'admin-rasio.html',            countUrl: null },
    { id: 'mdm-users',      icon: SVG_ICONS.users,     label: 'Manajemen User',   href: 'admin-users.html',            countUrl: '/admin/users' },
    { id: 'admin-riwayat',  icon: SVG_ICONS.riwayat,   label: 'Riwayat Perubahan',href: 'admin-riwayat.html',          countUrl: null },
  ];

  // ── Deteksi halaman saat ini ───────────────────────────────────────────────
  function _detectPage() {
    const filename = window.location.pathname.split('/').pop() || 'index.html';
    return PAGE_REGISTRY[filename] || { id: filename.replace('.html', ''), adminOnly: false, showAdminSubnav: false };
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
      ? `<div class="sb-wilayah-badge">${SVG_ICONS.harga} Wilayah: ${wilayah}</div>`
      : '';

    let html = `
      <div class="sb-brand">
        <div class="sb-logo">
          <span class="sb-logo-icon">${SVG_ICONS.logo}</span>
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
        html += `
          <a href="${item.href}" class="sb-item${active}" data-id="${item.id}">
            <span class="sb-icon">${item.icon}</span>
            <span class="sb-label">${item.label}</span>
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
              <span class="sb-chevron">${SVG_ICONS.chevron}</span>
            </button>
            <div class="sb-group-children">
        `;

        if (item.children) {
          item.children.forEach(child => {
            const childActive = child.id === activeId ? ' active' : '';
            html += `
              <a href="${child.href}" class="sb-child${childActive}" data-id="${child.id}">
                <span class="sb-child-icon">${child.icon}</span>
                <span class="sb-label">${child.label}</span>
              </a>
            `;
          });
        }

        html += `</div></div>`;
      }
    });

    html += `</nav>`;
    html += `
      <button class="sb-collapse-btn" id="sb-collapse-btn" onclick="LAYOUT.toggleCollapse()" title="Sembunyikan/tampilkan sidebar">
        <span class="sb-collapse-icon">${SVG_ICONS.collapse}</span>
      </button>
    `;

    let sidebar = document.querySelector('.sidebar, .mdm-sidebar, .cat-sidebar');
    if (sidebar) {
      sidebar.className = 'sb-sidebar';
      sidebar.id = 'app-sidebar';
      sidebar.innerHTML = html;
    } else {
      sidebar = document.createElement('aside');
      sidebar.className = 'sb-sidebar';
      sidebar.id = 'app-sidebar';
      sidebar.innerHTML = html;
      const shell = document.querySelector('.app-shell, .mdm-shell, .lk-shell, body');
      if (shell) shell.prepend(sidebar);
    }

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
    const collapsed = localStorage.getItem('sb_collapsed') === '1';
    if (collapsed) _applyCollapsed(true, false);

    if (window.innerWidth < 768) {
      _applyCollapsed(true, false);
    }

    let overlay = document.getElementById('sb-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'sb-overlay';
      overlay.className = 'sb-overlay';
      overlay.onclick = () => LAYOUT.toggleCollapse();
      document.body.appendChild(overlay);
    }

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
    btn.innerHTML = SVG_ICONS.hamburger;
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
      if (btn)  btn.querySelector('.sb-collapse-icon').innerHTML = SVG_ICONS.collapse;
      if (overlay && window.innerWidth < 768) overlay.classList.add('active');
    } else {
      sidebar.classList.remove('sb-collapsed');
      if (main) main.style.marginLeft = 'var(--sb-width, 240px)';
      if (btn)  btn.querySelector('.sb-collapse-icon').innerHTML = SVG_ICONS.collapse;
      if (overlay) overlay.classList.remove('active');
    }

    if (save) localStorage.setItem('sb_collapsed', collapsed ? '1' : '0');
  }

  // ── Admin guard ───────────────────────────────────────────────────────────
  function _adminGuard() {
    if (!AUTH.isAdmin()) {
      _showToast('Akses ditolak. Fitur ini hanya untuk Admin.', 'error');
      setTimeout(() => { window.location.href = 'index.html'; }, 1800);
      return false;
    }
    return true;
  }

  // ── Toast (fallback jika belum ada) ───────────────────────────────────────
  function _showToast(msg, type = 'info') {
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

  // ── Admin Sub-Sidebar (hanya untuk halaman master data) ───────────────────
  function _renderAdminSubSidebar(activeId) {
    const main = document.querySelector('.mdm-main, .main-content, .lk-main');
    if (!main || document.getElementById('admin-subnav')) return;

    const nav = document.createElement('aside');
    nav.id = 'admin-subnav';
    nav.className = 'admin-subnav';

    nav.innerHTML = `
      <div class="asn-header">
        <span class="asn-title">${SVG_ICONS.admin} Admin</span>
        <button class="asn-toggle" onclick="LAYOUT.toggleAdminSubnav()" title="Sembunyikan">${SVG_ICONS.chevron}</button>
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

    const children = Array.from(main.children).filter(el => el.id !== 'admin-subnav');
    const wrapper = document.createElement('div');
    wrapper.className = 'admin-content-wrap';
    children.forEach(el => wrapper.appendChild(el));
    main.appendChild(wrapper);

    _loadSubnavCounts();

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
      if (btn) btn.innerHTML = SVG_ICONS.chevron;
    } else {
      nav.classList.remove('asn-collapsed');
      if (btn) btn.innerHTML = SVG_ICONS.chevron;
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
    const showAdminSubnav = options.showAdminSubnav ?? pageConfig.showAdminSubnav;

    if (adminOnly && !_adminGuard()) return;

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        _renderSidebar(pageId);
        _setupCollapse();
        if (showAdminSubnav) _renderAdminSubSidebar(pageId);
      });
    } else {
      _renderSidebar(pageId);
      _setupCollapse();
      if (showAdminSubnav) _renderAdminSubSidebar(pageId);
    }
  }

  function toggleCollapse() {
    const sidebar = document.getElementById('app-sidebar');
    if (!sidebar) return;
    const isCollapsed = sidebar.classList.contains('sb-collapsed');
    _applyCollapsed(!isCollapsed);
  }

  function toggleGroup(groupId) {
    const group = document.querySelector(`[data-group="${groupId}"]`);
    if (!group) return;
    group.classList.toggle('open');
  }

  function requireAdmin() {
    if (!AUTH.isLoggedIn()) { AUTH.logout(); return false; }
    return _adminGuard();
  }

  return { init, toggleCollapse, toggleGroup, toggleAdminSubnav, requireAdmin };

})();