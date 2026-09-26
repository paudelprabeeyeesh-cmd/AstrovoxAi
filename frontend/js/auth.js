const API_BASE = (() => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('api_base') || 'http://localhost:8000';
  }
  return 'http://localhost:8000';
})();

const TOKEN_KEY = 'astrovox_access_token';
const REFRESH_TOKEN_KEY = 'astrovox_refresh_token';
const USER_KEY = 'astrovox_user';
const CSRF_KEY = 'astrovox_csrf_token';
const SESSION_EXPIRY_KEY = 'astrovox_session_expiry';

function getStoredToken() {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token && isTokenExpired()) {
      clearTokens();
      return null;
    }
    return token;
  } catch {
    return null;
  }
}

function getStoredRefreshToken() {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
}

function setTokens(accessToken, refreshToken, expiresIn = 3600) {
  localStorage.setItem(TOKEN_KEY, accessToken);
  if (refreshToken) localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  localStorage.setItem(SESSION_EXPIRY_KEY, Date.now() + expiresIn * 1000);
}

function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(CSRF_KEY);
  localStorage.removeItem(SESSION_EXPIRY_KEY);
}

function isTokenExpired() {
  const expiry = localStorage.getItem(SESSION_EXPIRY_KEY);
  if (!expiry) return true;
  return Date.now() > parseInt(expiry, 10);
}

function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function setStoredUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function getCsrfToken() {
  try {
    return localStorage.getItem(CSRF_KEY);
  } catch {
    return null;
  }
}

function setCsrfToken(token) {
  localStorage.setItem(CSRF_KEY, token);
}

function hasRole(role) {
  const user = getStoredUser();
  if (!user || !user.roles) return false;
  return user.roles.includes(role);
}

function hasPermission(permission) {
  const user = getStoredUser();
  if (!user || !user.permissions) return false;
  return user.permissions.includes(permission);
}

function getSessionTimeRemaining() {
  const expiry = localStorage.getItem(SESSION_EXPIRY_KEY);
  if (!expiry) return 0;
  return Math.max(0, parseInt(expiry, 10) - Date.now());
}

let refreshPromise = null;

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const refresh = getStoredRefreshToken();
    if (!refresh) return null;
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) {
        clearTokens();
        return null;
      }
      const data = await res.json();
      if (data.access_token) {
        localStorage.setItem(TOKEN_KEY, data.access_token);
      }
      return data.access_token;
    } catch {
      clearTokens();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

async function apiFetch(endpoint, options = {}) {
  let token = getStoredToken();
  const headers = {
    'Content-Type': 'application/json',
    'X-CSRF-Token': getCsrfToken() || '',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  let response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && endpoint !== '/auth/refresh') {
    token = await refreshAccessToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
      response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
      });
    }
  }

  if (response.status === 403) {
    console.warn('Forbidden: insufficient permissions');
  }

  return response;
}

class AuthAPI {
  static async login(email, password) {
    const res = await apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || err.message || 'Invalid email or password');
    }
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token, data.expires_in);
    setStoredUser({ id: data.user_id, email: data.email, roles: data.roles || [], permissions: data.permissions || [] });
    return data;
  }

  static async register(email, password, name) {
    const res = await apiFetch('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name: name }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail || err.message || 'Registration failed');
    }
    return res.json();
  }

  static async logout() {
    try {
      await apiFetch('/auth/logout', { method: 'POST' });
    } catch {
      // ignore
    } finally {
      clearTokens();
    }
  }

  static async refresh() {
    const token = await refreshAccessToken();
    return token;
  }

  static async getPermissions() {
    const res = await apiFetch('/auth/me/permissions');
    if (!res.ok) throw new Error('Failed to fetch permissions');
    return res.json();
  }

  static isAuthenticated() {
    return !!getStoredToken() && !isTokenExpired();
  }

  static getUser() {
    return getStoredUser();
  }

  static checkPermission(permission) {
    return hasPermission(permission);
  }

  static checkRole(role) {
    return hasRole(role);
  }

  static getSessionTimeRemaining() {
    return getSessionTimeRemaining();
  }
}

window.AuthAPI = AuthAPI;
