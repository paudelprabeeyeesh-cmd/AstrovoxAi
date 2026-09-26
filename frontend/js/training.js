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

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
    btn.classList.add('active');
    const panel = document.getElementById(btn.dataset.tab);
    if (panel) panel.classList.remove('hidden');
  });
});

async function buildDataset() {
  const name = document.getElementById('ds-name').value || 'dataset';
  const max = parseInt(document.getElementById('ds-max').value || '10000', 10);
  try {
    const data = await apiFetch('/training/dataset/build', {
      method: 'POST',
      body: JSON.stringify({ name, max_samples: max, train_split: 0.9 }),
    });
    document.getElementById('ds-output').textContent = JSON.stringify(data, null, 2);
    showSuccess('Dataset built');
  } catch (e) {
    showError(e.message);
  }
}

async function uploadDataset() {
  const fileInput = document.getElementById('ds-file');
  const name = document.getElementById('ds-name').value || 'dataset';
  if (!fileInput.files[0]) {
    showError('Select a JSONL file first');
    return;
  }
  const form = new FormData();
  form.append('file', fileInput.files[0]);
  form.append('name', name);
  try {
    const res = await fetch(`${API_BASE}/training/dataset/upload`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: form,
    });
    const data = await res.json();
    document.getElementById('ds-output').textContent = JSON.stringify(data, null, 2);
    showSuccess('Dataset uploaded');
  } catch (e) {
    showError(e.message);
  }
}

async function trainTokenizer() {
  const vocab = parseInt(document.getElementById('tok-vocab').value || '32000', 10);
  const minFreq = parseInt(document.getElementById('tok-min-freq').value || '2', 10);
  try {
    const data = await apiFetch('/training/tokenizer/train', {
      method: 'POST',
      body: JSON.stringify({ vocab_size: vocab, min_pair_freq: minFreq, texts: ['sample text for tokenizer training'] }),
    });
    document.getElementById('tok-output').textContent = JSON.stringify(data, null, 2);
    showSuccess('Tokenizer trained');
  } catch (e) {
    showError(e.message);
  }
}

async function createFineTuneJob() {
  const model = document.getElementById('ft-model').value || 'default';
  const useLora = document.getElementById('ft-lora').checked;
  const useQlora = document.getElementById('ft-qlora').checked;
  const rank = parseInt(document.getElementById('ft-rank').value || '8', 10);
  const lr = parseFloat(document.getElementById('ft-lr').value || '0.0001');
  try {
    const data = await apiFetch('/fine-tune/jobs', {
      method: 'POST',
      body: JSON.stringify({ model_name: model, use_lora: useLora, use_qlora: useQlora, lora_rank: rank, lr, batch_size: 8, num_epochs: 3 }),
    });
    document.getElementById('ft-output').textContent = JSON.stringify(data, null, 2);
    showSuccess('Fine-tune job created');
  } catch (e) {
    showError(e.message);
  }
}

async function injectLoRA() {
  const model = document.getElementById('ft-model').value || 'default';
  const rank = parseInt(document.getElementById('ft-rank').value || '8', 10);
  try {
    const data = await apiFetch('/fine-tune/lora/inject', {
      method: 'POST',
      body: JSON.stringify({ model_name: model, lora_rank: rank, lora_alpha: 16.0 }),
    });
    document.getElementById('ft-output').textContent = JSON.stringify(data, null, 2);
    showSuccess('LoRA injected');
  } catch (e) {
    showError(e.message);
  }
}

async function prepareQLoRA() {
  const model = document.getElementById('ft-model').value || 'default';
  const rank = parseInt(document.getElementById('ft-rank').value || '8', 10);
  try {
    const data = await apiFetch('/fine-tune/qlora/prepare', {
      method: 'POST',
      body: JSON.stringify({ model_name: model, qlora_bits: 4, lora_rank: rank }),
    });
    document.getElementById('ft-output').textContent = JSON.stringify(data, null, 2);
    showSuccess('QLoRA prepared');
  } catch (e) {
    showError(e.message);
  }
}

async function dpoTrain() {
  const model = document.getElementById('al-model').value || 'default';
  const beta = parseFloat(document.getElementById('al-beta').value || '0.1');
  try {
    const data = await apiFetch('/fine-tune/dpo/train', {
      method: 'POST',
      body: JSON.stringify({ model_name: model, beta, lr: 1e-5 }),
    });
    document.getElementById('al-output').textContent = JSON.stringify(data, null, 2);
    showSuccess('DPO step executed');
  } catch (e) {
    showError(e.message);
  }
}

async function rlhfTrain() {
  const model = document.getElementById('al-model').value || 'default';
  const kl = parseFloat(document.getElementById('al-kl').value || '0.1');
  try {
    const data = await apiFetch('/fine-tune/rlhf/train', {
      method: 'POST',
      body: JSON.stringify({ model_name: model, kl_coef: kl, lr: 1e-5 }),
    });
    document.getElementById('al-output').textContent = JSON.stringify(data, null, 2);
    showSuccess('RLHF step executed');
  } catch (e) {
    showError(e.message);
  }
}

async function runEvaluation() {
  const name = document.getElementById('ev-name').value || 'default';
  try {
    const data = await apiFetch('/training/evaluation/run', {
      method: 'POST',
      body: JSON.stringify({
        name,
        tasks: [
          { name: 'demo', prompt: 'Hello', expected: 'Hello', rubric: { pass_threshold: 0.5 } },
        ],
      }),
    });
    document.getElementById('ev-output').textContent = JSON.stringify(data, null, 2);
    showSuccess('Evaluation completed');
  } catch (e) {
    showError(e.message);
  }
}

async function mergeModels() {
  const method = document.getElementById('mg-method').value;
  try {
    const data = await apiFetch('/training/models/merge', {
      method: 'POST',
      body: JSON.stringify({ method }),
    });
    document.getElementById('mg-output').textContent = JSON.stringify(data, null, 2);
    showSuccess('Model merge completed');
  } catch (e) {
    showError(e.message);
  }
}
