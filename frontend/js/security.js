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

async function securityFetch(endpoint, options = {}) {
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
  const loadingEl = document.getElementById('security-loading');
  const errorEl = document.getElementById('security-error');
  const contentEl = document.getElementById('security-content');

  async function loadSecurity() {
    try {
      const data = await securityFetch('/security/overview');
      if (!data) throw new Error('Invalid response');
      if (loadingEl) loadingEl.style.display = 'none';
      if (errorEl) errorEl.style.display = 'none';
      if (contentEl) contentEl.style.display = 'block';

      const threatsEl = document.getElementById('stat-threats');
      const vulnsEl = document.getElementById('stat-vulns');
      const complianceEl = document.getElementById('stat-compliance');
      const incidentsEl = document.getElementById('stat-incidents');
      const threatsListEl = document.getElementById('threats-list');

      if (threatsEl) threatsEl.textContent = data.threats_blocked ?? 0;
      if (vulnsEl) vulnsEl.textContent = data.vulnerabilities ?? 0;
      if (complianceEl) complianceEl.textContent = (data.compliance_score ?? 0) + '%';
      if (incidentsEl) incidentsEl.textContent = data.active_incidents ?? 0;

      if (threatsListEl && Array.isArray(data.recent_threats)) {
        threatsListEl.innerHTML = data.recent_threats.map(threat => `
          <div style="display:flex;align-items:center;justify-content:space-between;padding:0.75rem;background:var(--bg-secondary);border:1px solid var(--border);border-radius:0.5rem;">
            <div>
              <div style="font-weight:600;font-size:0.875rem;">${escapeHtml(threat.type || 'Unknown')}</div>
              <div style="font-size:0.75rem;color:var(--text-muted);">${escapeHtml(threat.source || 'N/A')}</div>
            </div>
            <span style="font-size:0.75rem;padding:0.25rem 0.5rem;border-radius:9999px;background:${threat.severity === 'high' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)'};color:${threat.severity === 'high' ? 'var(--error)' : 'var(--warning)'};">${threat.severity || 'medium'}</span>
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

  loadSecurity();
});

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
