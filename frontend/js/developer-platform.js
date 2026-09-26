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

async function devPlatformFetch(endpoint, options = {}) {
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
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => {
        t.style.borderBottom = '2px solid transparent';
        t.style.color = 'var(--text-secondary)';
        t.style.fontWeight = '400';
      });
      tab.style.borderBottom = '2px solid var(--accent)';
      tab.style.color = 'var(--accent)';
      tab.style.fontWeight = '600';
      const target = tab.dataset.tab;
      document.getElementById('tab-api-keys').style.display = target === 'api-keys' ? 'block' : 'none';
      document.getElementById('tab-webhooks').style.display = target === 'webhooks' ? 'block' : 'none';
      document.getElementById('tab-logs').style.display = target === 'logs' ? 'block' : 'none';
      document.getElementById('tab-playground').style.display = target === 'playground' ? 'block' : 'none';
    });
  });

  loadApiKeys();

  document.getElementById('create-key-btn')?.addEventListener('click', async () => {
    try {
      const data = await devPlatformFetch('/developer/api-keys', {
        method: 'POST',
        body: JSON.stringify({ name: 'New Key', scopes: ['read', 'execute'] }),
      });
      showToast('API key created', 'success');
      loadApiKeys();
    } catch (err) {
      showError(err.message);
    }
  });

  document.getElementById('playground-run')?.addEventListener('click', async () => {
    const endpoint = document.getElementById('playground-endpoint')?.value;
    const bodyText = document.getElementById('playground-body')?.value;
    const resultEl = document.getElementById('playground-result');
    if (!endpoint || !bodyText) {
      showError('Please select an endpoint and enter a request body');
      return;
    }
    if (resultEl) resultEl.textContent = 'Sending...';
    try {
      const body = JSON.parse(bodyText);
      const data = await devPlatformFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify(body),
      });
      if (resultEl) resultEl.textContent = JSON.stringify(data, null, 2);
      showToast('Request completed', 'success');
    } catch (err) {
      if (resultEl) resultEl.textContent = `Error: ${err.message}`;
      showError(err.message);
    }
  });
});

async function loadApiKeys() {
  const loadingEl = document.getElementById('api-keys-loading');
  const tableEl = document.getElementById('api-keys-table');
  const tbody = tableEl?.querySelector('tbody');
  try {
    const data = await devPlatformFetch('/developer/api-keys');
    if (!data || !Array.isArray(data)) throw new Error('Invalid response');
    if (loadingEl) loadingEl.style.display = 'none';
    if (tableEl) tableEl.style.display = 'table';
    if (tbody) {
      tbody.innerHTML = data.map(key => `
        <tr style="border-bottom:1px solid var(--border);">
          <td style="padding:0.75rem;">${escapeHtml(key.name || 'Unnamed')}</td>
          <td style="padding:0.75rem;font-family:monospace;font-size:0.8rem;">${escapeHtml(key.key_prefix || '****')}...</td>
          <td style="padding:0.75rem;color:var(--text-secondary);font-size:0.875rem;">${escapeHtml(key.created || 'N/A')}</td>
          <td style="padding:0.75rem;color:var(--text-secondary);font-size:0.875rem;">${escapeHtml(key.expires || 'Never')}</td>
          <td style="padding:0.75rem;"><button class="btn btn-sm btn-secondary" style="padding:0.25rem 0.5rem;border-radius:0.375rem;background:var(--bg-tertiary);color:var(--text-primary);border:1px solid var(--border);cursor:pointer;font-size:0.75rem;" onclick="showToast('Revoke coming soon', 'success')">Revoke</button></td>
        </tr>
      `).join('');
    }
  } catch (err) {
    if (loadingEl) loadingEl.textContent = `Error: ${err.message}`;
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
