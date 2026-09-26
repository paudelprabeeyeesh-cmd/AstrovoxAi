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

async function audioFetch(endpoint, options = {}) {
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
      document.getElementById('tab-transcribe').style.display = target === 'transcribe' ? 'block' : 'none';
      document.getElementById('tab-synthesize').style.display = target === 'synthesize' ? 'block' : 'none';
      document.getElementById('tab-analyze').style.display = target === 'analyze' ? 'block' : 'none';
    });
  });

  document.getElementById('transcribe-btn')?.addEventListener('click', async () => {
    const fileInput = document.getElementById('audio-upload');
    const file = fileInput?.files?.[0];
    if (!file) {
      showError('Please upload an audio file');
      return;
    }
    const resultEl = document.getElementById('transcribe-result');
    if (resultEl) resultEl.textContent = 'Transcribing...';
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('language', document.getElementById('audio-language')?.value || 'en');
      const token = getToken();
      const res = await fetch(`${API_BASE}/audio/transcribe`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed' }));
        throw new Error(err.detail || err.message || `HTTP ${res.status}`);
      }
      const data = await res.json();
      if (resultEl) resultEl.textContent = data.transcript || data.text || JSON.stringify(data, null, 2);
      showToast('Transcription complete', 'success');
    } catch (err) {
      if (resultEl) resultEl.textContent = `Error: ${err.message}`;
      showError(err.message);
    }
  });

  document.getElementById('synthesize-btn')?.addEventListener('click', async () => {
    const text = document.getElementById('tts-text')?.value?.trim();
    if (!text) {
      showError('Please enter text to synthesize');
      return;
    }
    const voice = document.getElementById('tts-voice')?.value || 'alloy';
    const audioEl = document.getElementById('tts-audio');
    try {
      const data = await audioFetch('/audio/synthesize', {
        method: 'POST',
        body: JSON.stringify({ text, voice }),
      });
      if (data.audio_url && audioEl) {
        audioEl.src = data.audio_url;
        audioEl.style.display = 'block';
      } else if (audioEl) {
        audioEl.style.display = 'none';
      }
      showToast('Synthesis complete', 'success');
    } catch (err) {
      showError(err.message);
    }
  });

  document.getElementById('analyze-btn')?.addEventListener('click', async () => {
    const fileInput = document.getElementById('analyze-upload');
    const file = fileInput?.files?.[0];
    if (!file) {
      showError('Please upload an audio file');
      return;
    }
    const resultEl = document.getElementById('analyze-result');
    if (resultEl) resultEl.textContent = 'Analyzing...';
    try {
      const formData = new FormData();
      formData.append('file', file);
      const token = getToken();
      const res = await fetch(`${API_BASE}/audio/analyze`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed' }));
        throw new Error(err.detail || err.message || `HTTP ${res.status}`);
      }
      const data = await res.json();
      if (resultEl) resultEl.textContent = JSON.stringify(data, null, 2);
      showToast('Analysis complete', 'success');
    } catch (err) {
      if (resultEl) resultEl.textContent = `Error: ${err.message}`;
      showError(err.message);
    }
  });
});
