const API_BASE = (() => {
  try {
    return localStorage.getItem('api_base') || 'http://localhost:8000';
  } catch {
    return 'http://localhost:8000';
  }
})();

function getToken() {
  try {
    return localStorage.getItem('astrovox_access_token');
  } catch {
    return null;
  }
}

function showError(message) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast error';
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function showToast(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

async function integrationsFetch(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };
  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
  if (res.status === 401) {
    showError('Session expired. Please log in again.');
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || err.message || `HTTP ${res.status}`);
  }
  if (res.status === 204) return {};
  return res.json();
}

document.addEventListener('DOMContentLoaded', () => {
  const loadingEl = document.getElementById('integrations-loading');
  const errorEl = document.getElementById('integrations-error');
  const gridEl = document.getElementById('integrations-grid');

  async function loadIntegrations() {
    try {
      const data = await integrationsFetch('/integrations');
      if (!data || !Array.isArray(data)) {
        throw new Error('Invalid response');
      }
      if (loadingEl) loadingEl.style.display = 'none';
      if (errorEl) errorEl.style.display = 'none';
      if (gridEl) {
        gridEl.style.display = 'grid';
        gridEl.innerHTML = data.map(intg => `
          <div style="background:var(--bg-secondary);border:1px solid var(--border);border-radius:0.75rem;padding:1.25rem;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
              <h3 style="font-size:1rem;font-weight:600;">${escapeHtml(intg.name || 'Unnamed Integration')}</h3>
              <span style="font-size:0.75rem;padding:0.25rem 0.5rem;border-radius:9999px;background:${intg.connected ? 'rgba(34,197,94,0.15)' : 'rgba(100,116,139,0.15)'};color:${intg.connected ? 'var(--success)' : 'var(--text-muted)'};">${intg.connected ? 'Connected' : 'Available'}</span>
            </div>
            <p style="color:var(--text-secondary);font-size:0.875rem;margin-bottom:0.75rem;">${escapeHtml(intg.description || 'No description')}</p>
            <button class="btn btn-sm btn-primary" style="padding:0.35rem 0.75rem;border-radius:0.375rem;background:var(--accent);color:#fff;border:none;cursor:pointer;font-size:0.8rem;" onclick="showToast('${intg.connected ? 'Integration configured' : 'Connect flow coming soon'}', 'success')">${intg.connected ? 'Configure' : 'Connect'}</button>
          </div>
        `).join('');
      }
    } catch (err) {
      if (loadingEl) loadingEl.style.display = 'none';
      if (errorEl) {
        errorEl.style.display = 'block';
        errorEl.textContent = err.message;
      }
    }
  }

  loadIntegrations();
});

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
