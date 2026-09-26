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

async function inferenceFetch(endpoint, options = {}) {
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
  const loadingEl = document.getElementById('inference-loading');
  const errorEl = document.getElementById('inference-error');
  const gridEl = document.getElementById('endpoints-grid');
  const selectEl = document.getElementById('inference-endpoint-select');
  const deployBtn = document.getElementById('deploy-model-btn');

  if (deployBtn) {
    deployBtn.addEventListener('click', () => {
      showToast('Deploy model flow coming soon', 'success');
    });
  }

  async function loadEndpoints() {
    try {
      const data = await inferenceFetch('/inference/endpoints');
      if (!data || !Array.isArray(data)) {
        throw new Error('Invalid response');
      }
      if (loadingEl) loadingEl.style.display = 'none';
      if (errorEl) errorEl.style.display = 'none';
      if (gridEl) {
        gridEl.style.display = 'grid';
        gridEl.innerHTML = data.map(ep => `
          <div style="background:var(--bg-secondary);border:1px solid var(--border);border-radius:0.75rem;padding:1.25rem;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
              <h3 style="font-size:1rem;font-weight:600;">${escapeHtml(ep.name || 'Unnamed Endpoint')}</h3>
              <span style="font-size:0.75rem;padding:0.25rem 0.5rem;border-radius:9999px;background:${ep.status === 'healthy' ? 'rgba(34,197,94,0.15)' : 'rgba(245,158,11,0.15)'};color:${ep.status === 'healthy' ? 'var(--success)' : 'var(--warning)'};">${ep.status || 'unknown'}</span>
            </div>
            <p style="color:var(--text-secondary);font-size:0.875rem;margin-bottom:0.5rem;">Model: ${escapeHtml(ep.model || 'N/A')}</p>
            <p style="color:var(--text-secondary);font-size:0.875rem;margin-bottom:0.5rem;">Latency: ${ep.latency_ms != null ? ep.latency_ms + 'ms' : 'N/A'}</p>
            <p style="color:var(--text-secondary);font-size:0.875rem;margin-bottom:0.75rem;">Requests/min: ${ep.requests_per_minute != null ? ep.requests_per_minute : 'N/A'}</p>
            <button class="btn btn-sm btn-secondary" style="padding:0.35rem 0.75rem;border-radius:0.375rem;background:var(--bg-tertiary);color:var(--text-primary);border:1px solid var(--border);cursor:pointer;font-size:0.8rem;" onclick="showToast('Endpoint details coming soon', 'success')">Details</button>
          </div>
        `).join('');
      }
      if (selectEl) {
        selectEl.innerHTML = '<option value="">Select an endpoint...</option>' + data.map(ep => `<option value="${escapeHtml(ep.id || ep.name)}">${escapeHtml(ep.name)}</option>`).join('');
      }
    } catch (err) {
      if (loadingEl) loadingEl.style.display = 'none';
      if (errorEl) {
        errorEl.style.display = 'block';
        errorEl.textContent = err.message;
      }
    }
  }

  loadEndpoints();

  document.getElementById('run-inference-btn')?.addEventListener('click', async () => {
    const endpoint = selectEl?.value;
    const prompt = document.getElementById('inference-prompt')?.value?.trim();
    if (!endpoint || !prompt) {
      showError('Please select an endpoint and enter a prompt');
      return;
    }
    const resultEl = document.getElementById('inference-result');
    if (resultEl) resultEl.textContent = 'Running inference...';
    try {
      const data = await inferenceFetch('/inference/run', {
        method: 'POST',
        body: JSON.stringify({ endpoint_id: endpoint, prompt }),
      });
      if (resultEl) resultEl.textContent = data.result || data.output || JSON.stringify(data, null, 2);
      showToast('Inference complete', 'success');
    } catch (err) {
      if (resultEl) resultEl.textContent = `Error: ${err.message}`;
      showError(err.message);
    }
  });
});

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
