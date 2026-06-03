/**
 * auth.js — SIKALTARA Authentication Guard
 * Manajemen token JWT di localStorage + auth guard untuk semua halaman.
 *
 * Penggunaan:
 *   <script src="js/auth.js"></script>   ← PERTAMA, sebelum script lain
 *   <script>AUTH.requireAuth();</script> ← setelah tag di atas
 */

const AUTH = (() => {
  // ── Key localStorage ──────────────────────────────────────────────────────
  const K = {
    token:      'sikaltar_token',
    role:       'sikaltar_role',
    wilayah:    'sikaltar_wilayah',
    nama:       'sikaltar_nama',
    mustChange: 'sikaltar_must_change',
  };

  // Deteksi base path secara dinamis (/app/* atau root)
  const _basePath = (() => {
    const p = window.location.pathname;
    // Jika di-serve di /app/*, base = '/app'
    if (p.startsWith('/app')) return '/app';
    // Jika di root langsung
    return '';
  })();
  const LOGIN_PAGE = _basePath + '/login.html';

  // ── Token helpers ──────────────────────────────────────────────────────────

  function getToken()       { return localStorage.getItem(K.token); }
  function getRole()        { return localStorage.getItem(K.role); }
  function getWilayahKode() { return localStorage.getItem(K.wilayah) || null; }
  function getNama()        { return localStorage.getItem(K.nama) || 'Pengguna'; }
  function isAdmin()        { return getRole() === 'admin'; }

  /** Decode JWT payload (client-side only, tanpa verifikasi signature). */
  function decodePayload(token) {
    try {
      const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      const pad  = b64 + '='.repeat((4 - b64.length % 4) % 4);
      return JSON.parse(atob(pad));
    } catch {
      return null;
    }
  }

  /** Cek apakah token sudah expired berdasarkan claim exp. */
  function isExpired() {
    const token = getToken();
    if (!token) return true;
    const payload = decodePayload(token);
    if (!payload || !payload.exp) return true;
    return (Date.now() / 1000) > payload.exp;
  }

  function isLoggedIn() { return !!getToken() && !isExpired(); }

  // ── Bersihkan localStorage ─────────────────────────────────────────────────

  function _clearStorage() {
    Object.values(K).forEach(k => localStorage.removeItem(k));
  }

  // ── Login ──────────────────────────────────────────────────────────────────

  /**
   * POST /auth/login → simpan token + info ke localStorage.
   * @returns {Promise<object>} TokenResponse
   */
  async function login(username, password) {
    const res = await fetch('/auth/login', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Username atau password salah.');
    }

    const data = await res.json();
    localStorage.setItem(K.token,      data.access_token);
    localStorage.setItem(K.role,       data.role);
    localStorage.setItem(K.wilayah,    data.wilayah_kode || '');
    localStorage.setItem(K.nama,       data.nama || username);
    localStorage.setItem(K.mustChange, data.must_change_password ? '1' : '0');
    return data;
  }

  // ── Logout ─────────────────────────────────────────────────────────────────

  function logout() {
    const token = getToken();
    if (token) {
      // Beritahu server (fire and forget — tidak menunggu response)
      fetch('/auth/logout', {
        method:  'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      }).catch(() => {});
    }
    _clearStorage();
    window.location.href = LOGIN_PAGE;
  }

  // ── Auth Guard ─────────────────────────────────────────────────────────────

  /**
   * Panggil di setiap halaman (kecuali login.html).
   * Jika tidak login / token expired → redirect ke login.
   */
  function requireAuth() {
    if (!isLoggedIn()) {
      _clearStorage();
      window.location.href = LOGIN_PAGE;
      return false;
    }
    // Render user info di header setelah DOM siap
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', _renderUserNav);
    } else {
      _renderUserNav();
    }
    return true;
  }

  // ── Render User Info di Navbar ─────────────────────────────────────────────

  function _renderUserNav() {
    // Idempoten: jangan render ulang jika sudah ada
    if (document.getElementById('auth-user-nav')) return;

    const nama    = getNama();
    const role    = getRole();
    const wilayah = getWilayahKode();

    const roleLabel    = role === 'admin' ? 'Admin' : 'Operator';
    const roleClass    = role === 'admin' ? 'badge-blue' : 'badge-green';
    const wilayahBadge = (role !== 'admin' && wilayah)
      ? `<span class="badge badge-yellow" title="Wilayah akses Anda">📍 ${wilayah}</span>`
      : '';

    const navHtml = `
      <div id="auth-user-nav" style="display:flex;align-items:center;gap:8px;flex-shrink:0">
        <span style="font-size:0.82rem;color:var(--text-muted,#718096);font-weight:500;white-space:nowrap">
          👤 ${_escapeHtml(nama)}
        </span>
        <span class="badge ${roleClass}">${roleLabel}</span>
        ${wilayahBadge}
        <button
          id="btn-logout"
          onclick="AUTH.logout()"
          class="btn btn-ghost btn-sm"
          title="Keluar dari SIKALTARA"
        >⏻ Keluar</button>
      </div>
    `;

    // Prioritas: .header-actions → .page-header → .lk-header → .mdm-topbar
    const target =
      document.querySelector('.header-actions') ||
      document.querySelector('.page-header')    ||
      document.querySelector('.lk-header')      ||
      document.querySelector('.mdm-topbar');

    if (target) {
      target.insertAdjacentHTML('beforeend', navHtml);
    }
  }

  /** Escape HTML untuk keamanan tampilan nama user. */
  function _escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  return {
    login,
    logout,
    requireAuth,
    getToken,
    getRole,
    getWilayahKode,
    getNama,
    isAdmin,
    isLoggedIn,
    decodePayload,
  };
})();
