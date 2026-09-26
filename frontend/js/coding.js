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

async function codingFetch(endpoint, options = {}) {
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
  const promptEl = document.getElementById('code-prompt');
  const outputEl = document.getElementById('code-output');
  const langEl = document.getElementById('code-language');

  document.getElementById('generate-code-btn')?.addEventListener('click', async () => {
    const prompt = promptEl?.value?.trim();
    if (!prompt) {
      showError('Please enter a prompt');
      return;
    }
    const language = langEl?.value || 'python';
    if (outputEl) outputEl.textContent = 'Generating...';
    try {
      const data = await codingFetch('/code/generate', {
        method: 'POST',
        body: JSON.stringify({ prompt, language }),
      });
      if (outputEl) outputEl.textContent = data.code || data.result || JSON.stringify(data, null, 2);
      showToast('Code generated', 'success');
    } catch (err) {
      if (outputEl) outputEl.textContent = `Error: ${err.message}`;
      showError(err.message);
    }
  });

  document.getElementById('explain-code-btn')?.addEventListener('click', async () => {
    const prompt = promptEl?.value?.trim();
    if (!prompt) {
      showError('Please enter code or a prompt to explain');
      return;
    }
    if (outputEl) outputEl.textContent = 'Explaining...';
    try {
      const data = await codingFetch('/code/explain', {
        method: 'POST',
        body: JSON.stringify({ code: prompt }),
      });
      if (outputEl) outputEl.textContent = data.explanation || data.result || JSON.stringify(data, null, 2);
      showToast('Explanation ready', 'success');
    } catch (err) {
      if (outputEl) outputEl.textContent = `Error: ${err.message}`;
      showError(err.message);
    }
  });

  document.getElementById('review-code-btn')?.addEventListener('click', async () => {
    const prompt = promptEl?.value?.trim();
    if (!prompt) {
      showError('Please enter code to review');
      return;
    }
    if (outputEl) outputEl.textContent = 'Reviewing...';
    try {
      const data = await codingFetch('/code/review', {
        method: 'POST',
        body: JSON.stringify({ code: prompt }),
      });
      if (outputEl) outputEl.textContent = data.review || data.result || JSON.stringify(data, null, 2);
      showToast('Review ready', 'success');
    } catch (err) {
      if (outputEl) outputEl.textContent = `Error: ${err.message}`;
      showError(err.message);
    }
  });

  document.getElementById('copy-code-btn')?.addEventListener('click', () => {
    const text = outputEl?.textContent;
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard', 'success')).catch(() => showError('Failed to copy', 'error'));
  });
});
