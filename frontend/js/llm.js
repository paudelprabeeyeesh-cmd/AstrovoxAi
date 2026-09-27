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

async function apiFetch(endpoint, options = {}) {
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

function showSuccess(message) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast success';
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 3000);
  }, 3000);
}

document.getElementById('send-btn')?.addEventListener('click', async () => {
  const input = document.getElementById('chat-input');
  const output = document.getElementById('chat-output');
  const message = input.value.trim();
  if (!message) return;

  output.textContent += `\nYou: ${message}\n`;
  input.value = '';

  try {
    const data = await apiFetch('/llm/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
    output.textContent += `AI: ${data.response}\n`;
    output.scrollTop = output.scrollHeight;
    showSuccess('Response received');
  } catch (e) {
    showError(e.message);
  }
});

document.getElementById('generate-btn')?.addEventListener('click', async () => {
  const prompt = document.getElementById('gen-prompt').value.trim();
  const maxTokens = parseInt(document.getElementById('gen-tokens').value || '200', 10);
  const temperature = parseFloat(document.getElementById('gen-temp').value || '0.8');
  const output = document.getElementById('gen-output');
  if (!prompt) return;

  try {
    const data = await apiFetch('/llm/generate', {
      method: 'POST',
      body: JSON.stringify({ prompt, max_new_tokens: maxTokens, temperature }),
    });
    output.textContent = data.text;
    showSuccess('Generation complete');
  } catch (e) {
    showError(e.message);
  }
});
