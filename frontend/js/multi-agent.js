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

async function multiAgentFetch(endpoint, options = {}) {
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
  const loadingEl = document.getElementById('workflows-loading');
  const errorEl = document.getElementById('workflows-error');
  const listEl = document.getElementById('workflows-list');
  const createBtn = document.getElementById('create-workflow-btn');

  if (createBtn) {
    createBtn.addEventListener('click', () => {
      showToast('Create workflow flow coming soon', 'success');
    });
  }

  async function loadWorkflows() {
    try {
      const data = await multiAgentFetch('/multi-agent/workflows');
      if (!data || !Array.isArray(data)) {
        throw new Error('Invalid response');
      }
      if (loadingEl) loadingEl.style.display = 'none';
      if (errorEl) errorEl.style.display = 'none';
      if (listEl) {
        listEl.style.display = 'flex';
        listEl.innerHTML = data.map(wf => `
          <div style="background:var(--bg-secondary);border:1px solid var(--border);border-radius:0.75rem;padding:1.25rem;display:flex;align-items:center;justify-content:space-between;">
            <div>
              <h3 style="font-size:1rem;font-weight:600;margin-bottom:0.25rem;">${escapeHtml(wf.name || 'Unnamed Workflow')}</h3>
              <p style="color:var(--text-secondary);font-size:0.875rem;">Agents: ${(wf.agents || []).map(a => escapeHtml(a)).join(', ') || 'None'}</p>
            </div>
            <div style="display:flex;gap:0.5rem;">
              <button class="btn btn-sm btn-primary" style="padding:0.35rem 0.75rem;border-radius:0.375rem;background:var(--accent);color:#fff;border:none;cursor:pointer;font-size:0.8rem;" onclick="showToast('Workflow run coming soon', 'success')">Run</button>
              <button class="btn btn-sm btn-secondary" style="padding:0.35rem 0.75rem;border-radius:0.375rem;background:var(--bg-tertiary);color:var(--text-primary);border:1px solid var(--border);cursor:pointer;font-size:0.8rem;" onclick="showToast('Workflow config coming soon', 'success')">Configure</button>
            </div>
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

  loadWorkflows();
});

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
