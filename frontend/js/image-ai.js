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

async function imageAiFetch(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    showError('Session expired. Please log in again.');
    setTimeout(() => { window.location.href = '/login.html'; }, 2000);
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }

  if (res.status === 204) return {};
  return res.json();
}

class ImageAIApp {
  constructor() {
    this.currentTab = 'generate';
    this.init();
  }

  init() {
    const app = document.getElementById('app');
    if (!app) return;

    app.innerHTML = `
      <div class="navbar">
        <a href="/dashboard.html" class="navbar-brand">
          <div class="logo">A</div>
          <span>AstrovoxAI</span>
        </a>
        <nav class="navbar-nav">
          <a href="/chat.html" class="nav-link">Chat</a>
          <a href="/dashboard.html" class="nav-link">Dashboard</a>
          <a href="/image-ai.html" class="nav-link active">Image AI</a>
          <div class="nav-user">
            <span style="font-size: 0.875rem; color: var(--text-secondary);">${getUser()?.email || 'User'}</span>
            <button class="btn btn-sm btn-secondary" id="logout-btn">Logout</button>
          </div>
        </nav>
      </div>
      <div class="page-content">
        <div class="container">
          <h1 style="font-size: 1.875rem; font-weight: 700; margin-bottom: 0.5rem;">Image AI Studio</h1>
          <p style="color: var(--text-muted); font-size: 0.875rem; margin-bottom: 1.5rem;">Generate, edit, analyze, and understand images with AI.</p>

          <div class="tabs" style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap;">
            <button class="tab-btn active" data-tab="generate">Text-to-Image</button>
            <button class="tab-btn" data-tab="img2img">Image-to-Image</button>
            <button class="tab-btn" data-tab="inpaint">Inpainting</button>
            <button class="tab-btn" data-tab="outpaint">Outpainting</button>
            <button class="tab-btn" data-tab="bg-removal">Background Removal</button>
            <button class="tab-btn" data-tab="face-restore">Face Restoration</button>
            <button class="tab-btn" data-tab="super-res">Super Resolution</button>
            <button class="tab-btn" data-tab="ocr">OCR</button>
            <button class="tab-btn" data-tab="detect">Object Detection</button>
            <button class="tab-btn" data-tab="segment">Segmentation</button>
          </div>

          <div id="tab-content"></div>
        </div>
      </div>
    `;

    document.getElementById('logout-btn')?.addEventListener('click', () => this.handleLogout());
    this.bindTabs();
    this.showTab('generate');
  }

  bindTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.showTab(btn.dataset.tab);
      });
    });
  }

  showTab(tab) {
    this.currentTab = tab;
    const container = document.getElementById('tab-content');
    if (!container) return;

    const renderers = {
      generate: () => this.renderGenerate(container),
      img2img: () => this.renderImg2Img(container),
      inpaint: () => this.renderInpaint(container),
      outpaint: () => this.renderOutpaint(container),
      'bg-removal': () => this.renderBgRemoval(container),
      'face-restore': () => this.renderFaceRestore(container),
      'super-res': () => this.renderSuperRes(container),
      ocr: () => this.renderOcr(container),
      detect: () => this.renderDetect(container),
      segment: () => this.renderSegment(container),
    };

    const renderer = renderers[tab];
    if (renderer) renderer();
  }

  renderGenerate(container) {
    container.innerHTML = `
      <div class="card" style="padding: 1.5rem;">
        <h2 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem;">Text-to-Image</h2>
        <div class="form-group">
          <label>Prompt</label>
          <textarea id="txt2img-prompt" rows="3" placeholder="A futuristic city at sunset..."></textarea>
        </div>
        <div class="form-group">
          <label>Negative Prompt</label>
          <textarea id="txt2img-neg" rows="2" placeholder="blurry, low quality"></textarea>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 1rem;">
          <div class="form-group">
            <label>Width</label>
            <input type="number" id="txt2img-width" value="1024" />
          </div>
          <div class="form-group">
            <label>Height</label>
            <input type="number" id="txt2img-height" value="1024" />
          </div>
          <div class="form-group">
            <label>Steps</label>
            <input type="number" id="txt2img-steps" value="30" />
          </div>
          <div class="form-group">
            <label>Guidance</label>
            <input type="number" id="txt2img-guidance" value="7.5" step="0.5" />
          </div>
        </div>
        <button class="btn btn-primary" id="txt2img-btn" style="margin-top: 1rem;">Generate Image</button>
        <div id="txt2img-result" style="margin-top: 1rem;"></div>
      </div>
    `;
    document.getElementById('txt2img-btn')?.addEventListener('click', () => this.handleGenerate());
  }

  renderImg2Img(container) {
    container.innerHTML = `
      <div class="card" style="padding: 1.5rem;">
        <h2 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem;">Image-to-Image</h2>
        <div class="form-group">
          <label>Input Image</label>
          <input type="file" id="img2img-file" accept="image/*" />
        </div>
        <div class="form-group">
          <label>Prompt</label>
          <textarea id="img2img-prompt" rows="3" placeholder="Transform into a painting..."></textarea>
        </div>
        <div class="form-group">
          <label>Strength</label>
          <input type="number" id="img2img-strength" value="0.75" min="0" max="1" step="0.05" />
        </div>
        <button class="btn btn-primary" id="img2img-btn" style="margin-top: 1rem;">Transform</button>
        <div id="img2img-result" style="margin-top: 1rem;"></div>
      </div>
    `;
    document.getElementById('img2img-btn')?.addEventListener('click', () => this.handleImg2Img());
  }

  renderInpaint(container) {
    container.innerHTML = `
      <div class="card" style="padding: 1.5rem;">
        <h2 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem;">Inpainting</h2>
        <div class="form-group">
          <label>Image</label>
          <input type="file" id="inpaint-image" accept="image/*" />
        </div>
        <div class="form-group">
          <label>Mask (white = inpaint area)</label>
          <input type="file" id="inpaint-mask" accept="image/*" />
        </div>
        <div class="form-group">
          <label>Prompt</label>
          <textarea id="inpaint-prompt" rows="3" placeholder="A red apple on the table"></textarea>
        </div>
        <button class="btn btn-primary" id="inpaint-btn" style="margin-top: 1rem;">Inpaint</button>
        <div id="inpaint-result" style="margin-top: 1rem;"></div>
      </div>
    `;
    document.getElementById('inpaint-btn')?.addEventListener('click', () => this.handleInpaint());
  }

  renderOutpaint(container) {
    container.innerHTML = `
      <div class="card" style="padding: 1.5rem;">
        <h2 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem;">Outpainting</h2>
        <div class="form-group">
          <label>Image</label>
          <input type="file" id="outpaint-file" accept="image/*" />
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 1rem;">
          <div class="form-group">
            <label>Top</label>
            <input type="number" id="outpaint-top" value="128" />
          </div>
          <div class="form-group">
            <label>Bottom</label>
            <input type="number" id="outpaint-bottom" value="128" />
          </div>
          <div class="form-group">
            <label>Left</label>
            <input type="number" id="outpaint-left" value="128" />
          </div>
          <div class="form-group">
            <label>Right</label>
            <input type="number" id="outpaint-right" value="128" />
          </div>
        </div>
        <div class="form-group">
          <label>Prompt</label>
          <input type="text" id="outpaint-prompt" placeholder="extend the scene naturally" />
        </div>
        <button class="btn btn-primary" id="outpaint-btn" style="margin-top: 1rem;">Outpaint</button>
        <div id="outpaint-result" style="margin-top: 1rem;"></div>
      </div>
    `;
    document.getElementById('outpaint-btn')?.addEventListener('click', () => this.handleOutpaint());
  }

  renderBgRemoval(container) {
    container.innerHTML = `
      <div class="card" style="padding: 1.5rem;">
        <h2 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem;">Background Removal</h2>
        <div class="form-group">
          <label>Image</label>
          <input type="file" id="bg-file" accept="image/*" />
        </div>
        <button class="btn btn-primary" id="bg-btn" style="margin-top: 1rem;">Remove Background</button>
        <div id="bg-result" style="margin-top: 1rem;"></div>
      </div>
    `;
    document.getElementById('bg-btn')?.addEventListener('click', () => this.handleBgRemoval());
  }

  renderFaceRestore(container) {
    container.innerHTML = `
      <div class="card" style="padding: 1.5rem;">
        <h2 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem;">Face Restoration</h2>
        <div class="form-group">
          <label>Image</label>
          <input type="file" id="face-file" accept="image/*" />
        </div>
        <button class="btn btn-primary" id="face-btn" style="margin-top: 1rem;">Restore Face</button>
        <div id="face-result" style="margin-top: 1rem;"></div>
      </div>
    `;
    document.getElementById('face-btn')?.addEventListener('click', () => this.handleFaceRestore());
  }

  renderSuperRes(container) {
    container.innerHTML = `
      <div class="card" style="padding: 1.5rem;">
        <h2 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem;">Super Resolution</h2>
        <div class="form-group">
          <label>Image</label>
          <input type="file" id="sr-file" accept="image/*" />
        </div>
        <div class="form-group">
          <label>Scale</label>
          <select id="sr-scale">
            <option value="2">2x</option>
            <option value="4" selected>4x</option>
          </select>
        </div>
        <button class="btn btn-primary" id="sr-btn" style="margin-top: 1rem;">Upscale</button>
        <div id="sr-result" style="margin-top: 1rem;"></div>
      </div>
    `;
    document.getElementById('sr-btn')?.addEventListener('click', () => this.handleSuperRes());
  }

  renderOcr(container) {
    container.innerHTML = `
      <div class="card" style="padding: 1.5rem;">
        <h2 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem;">OCR</h2>
        <div class="form-group">
          <label>Image</label>
          <input type="file" id="ocr-file" accept="image/*" />
        </div>
        <button class="btn btn-primary" id="ocr-btn" style="margin-top: 1rem;">Extract Text</button>
        <div id="ocr-result" style="margin-top: 1rem; white-space: pre-wrap;"></div>
      </div>
    `;
    document.getElementById('ocr-btn')?.addEventListener('click', () => this.handleOcr());
  }

  renderDetect(container) {
    container.innerHTML = `
      <div class="card" style="padding: 1.5rem;">
        <h2 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem;">Object Detection</h2>
        <div class="form-group">
          <label>Image</label>
          <input type="file" id="detect-file" accept="image/*" />
        </div>
        <div class="form-group">
          <label>Threshold</label>
          <input type="number" id="detect-threshold" value="0.5" min="0" max="1" step="0.1" />
        </div>
        <button class="btn btn-primary" id="detect-btn" style="margin-top: 1rem;">Detect Objects</button>
        <div id="detect-result" style="margin-top: 1rem;"></div>
      </div>
    `;
    document.getElementById('detect-btn')?.addEventListener('click', () => this.handleDetect());
  }

  renderSegment(container) {
    container.innerHTML = `
      <div class="card" style="padding: 1.5rem;">
        <h2 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem;">Segmentation</h2>
        <div class="form-group">
          <label>Image</label>
          <input type="file" id="segment-file" accept="image/*" />
        </div>
        <button class="btn btn-primary" id="segment-btn" style="margin-top: 1rem;">Segment</button>
        <div id="segment-result" style="margin-top: 1rem;"></div>
      </div>
    `;
    document.getElementById('segment-btn')?.addEventListener('click', () => this.handleSegment());
  }

  async uploadFile(inputId) {
    const input = document.getElementById(inputId);
    if (!input || !input.files?.[0]) {
      showError('Please select a file');
      throw new Error('No file');
    }
    const formData = new FormData();
    formData.append('file', input.files[0]);
    const res = await fetch(`${API_BASE}/files/upload`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error('Upload failed');
    const data = await res.json();
    return data.url;
  }

  async handleGenerate() {
    const prompt = document.getElementById('txt2img-prompt')?.value?.trim();
    if (!prompt) return showError('Prompt is required');
    const btn = document.getElementById('txt2img-btn');
    btn.disabled = true;
    btn.textContent = 'Generating...';
    try {
      const formData = new FormData();
      formData.append('prompt', prompt);
      formData.append('negative_prompt', document.getElementById('txt2img-neg')?.value || '');
      formData.append('width', document.getElementById('txt2img-width')?.value || '1024');
      formData.append('height', document.getElementById('txt2img-height')?.value || '1024');
      formData.append('num_inference_steps', document.getElementById('txt2img-steps')?.value || '30');
      formData.append('guidance_scale', document.getElementById('txt2img-guidance')?.value || '7.5');
      const res = await fetch(`${API_BASE}/images/generate`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Generation failed');
      const data = await res.json();
      document.getElementById('txt2img-result').innerHTML = `
        <img src="data:${data.mime_type};base64,${data.data}" style="max-width: 100%; border-radius: 0.5rem; border: 1px solid var(--border);" />
        <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.5rem;">Seed: ${data.seed || 'N/A'} | ${data.width}x${data.height}</p>
      `;
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Generate Image';
    }
  }

  async handleImg2Img() {
    const prompt = document.getElementById('img2img-prompt')?.value?.trim();
    if (!prompt) return showError('Prompt is required');
    const fileInput = document.getElementById('img2img-file');
    if (!fileInput?.files?.[0]) return showError('Select an image');
    const btn = document.getElementById('img2img-btn');
    btn.disabled = true;
    btn.textContent = 'Transforming...';
    try {
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      formData.append('prompt', prompt);
      formData.append('strength', document.getElementById('img2img-strength')?.value || '0.75');
      const res = await fetch(`${API_BASE}/images/transform/img2img`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Transform failed');
      const data = await res.json();
      document.getElementById('img2img-result').innerHTML = `
        <img src="data:${data.mime_type};base64,${data.data}" style="max-width: 100%; border-radius: 0.5rem; border: 1px solid var(--border);" />
      `;
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Transform';
    }
  }

  async handleInpaint() {
    const prompt = document.getElementById('inpaint-prompt')?.value?.trim();
    if (!prompt) return showError('Prompt is required');
    const imageInput = document.getElementById('inpaint-image');
    const maskInput = document.getElementById('inpaint-mask');
    if (!imageInput?.files?.[0] || !maskInput?.files?.[0]) return showError('Select image and mask');
    const btn = document.getElementById('inpaint-btn');
    btn.disabled = true;
    btn.textContent = 'Inpainting...';
    try {
      const formData = new FormData();
      formData.append('image_file', imageInput.files[0]);
      formData.append('mask_file', maskInput.files[0]);
      formData.append('prompt', prompt);
      const res = await fetch(`${API_BASE}/images/transform/inpaint`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Inpainting failed');
      const data = await res.json();
      document.getElementById('inpaint-result').innerHTML = `
        <img src="data:${data.mime_type};base64,${data.data}" style="max-width: 100%; border-radius: 0.5rem; border: 1px solid var(--border);" />
      `;
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Inpaint';
    }
  }

  async handleOutpaint() {
    const fileInput = document.getElementById('outpaint-file');
    if (!fileInput?.files?.[0]) return showError('Select an image');
    const btn = document.getElementById('outpaint-btn');
    btn.disabled = true;
    btn.textContent = 'Outpainting...';
    try {
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      formData.append('expand_top', document.getElementById('outpaint-top')?.value || '0');
      formData.append('expand_bottom', document.getElementById('outpaint-bottom')?.value || '0');
      formData.append('expand_left', document.getElementById('outpaint-left')?.value || '0');
      formData.append('expand_right', document.getElementById('outpaint-right')?.value || '0');
      formData.append('prompt', document.getElementById('outpaint-prompt')?.value || '');
      const res = await fetch(`${API_BASE}/images/transform/outpaint`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Outpainting failed');
      const data = await res.json();
      document.getElementById('outpaint-result').innerHTML = `
        <img src="data:${data.mime_type};base64,${data.data}" style="max-width: 100%; border-radius: 0.5rem; border: 1px solid var(--border);" />
      `;
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Outpaint';
    }
  }

  async handleBgRemoval() {
    const fileInput = document.getElementById('bg-file');
    if (!fileInput?.files?.[0]) return showError('Select an image');
    const btn = document.getElementById('bg-btn');
    btn.disabled = true;
    btn.textContent = 'Removing...';
    try {
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      const res = await fetch(`${API_BASE}/images/edit/remove-background`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Background removal failed');
      const data = await res.json();
      document.getElementById('bg-result').innerHTML = `
        <img src="data:${data.mime_type};base64,${data.data}" style="max-width: 100%; border-radius: 0.5rem; border: 1px solid var(--border); background: linear-gradient(45deg, #ccc 25%, transparent 25%), linear-gradient(-45deg, #ccc 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #ccc 75%), linear-gradient(-45deg, transparent 75%, #ccc 75%); background-size: 20px 20px; background-position: 0 0, 0 10px, 10px -10px, -10px 0px;" />
      `;
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Remove Background';
    }
  }

  async handleFaceRestore() {
    const fileInput = document.getElementById('face-file');
    if (!fileInput?.files?.[0]) return showError('Select an image');
    const btn = document.getElementById('face-btn');
    btn.disabled = true;
    btn.textContent = 'Restoring...';
    try {
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      const res = await fetch(`${API_BASE}/images/edit/restore-face`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Face restoration failed');
      const data = await res.json();
      document.getElementById('face-result').innerHTML = `
        <img src="data:${data.mime_type};base64,${data.data}" style="max-width: 100%; border-radius: 0.5rem; border: 1px solid var(--border);" />
      `;
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Restore Face';
    }
  }

  async handleSuperRes() {
    const fileInput = document.getElementById('sr-file');
    if (!fileInput?.files?.[0]) return showError('Select an image');
    const btn = document.getElementById('sr-btn');
    btn.disabled = true;
    btn.textContent = 'Upscaling...';
    try {
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      formData.append('scale', document.getElementById('sr-scale')?.value || '4');
      const res = await fetch(`${API_BASE}/images/edit/super-resolve`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Super resolution failed');
      const data = await res.json();
      document.getElementById('sr-result').innerHTML = `
        <img src="data:${data.mime_type};base64,${data.data}" style="max-width: 100%; border-radius: 0.5rem; border: 1px solid var(--border);" />
        <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.5rem;">Scale: ${data.scale}x</p>
      `;
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Upscale';
    }
  }

  async handleOcr() {
    const fileInput = document.getElementById('ocr-file');
    if (!fileInput?.files?.[0]) return showError('Select an image');
    const btn = document.getElementById('ocr-btn');
    btn.disabled = true;
    btn.textContent = 'Extracting...';
    try {
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      const res = await fetch(`${API_BASE}/images/analyze/ocr`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('OCR failed');
      const data = await res.json();
      document.getElementById('ocr-result').innerHTML = `
        <div class="card" style="padding: 1rem; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 0.5rem;">
          <h3 style="font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;">Extracted Text</h3>
          <p style="white-space: pre-wrap;">${data.text || '(no text detected)'}</p>
          ${data.blocks?.length ? `<p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.5rem;">${data.blocks.length} text block(s)</p>` : ''}
        </div>
      `;
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Extract Text';
    }
  }

  async handleDetect() {
    const fileInput = document.getElementById('detect-file');
    if (!fileInput?.files?.[0]) return showError('Select an image');
    const btn = document.getElementById('detect-btn');
    btn.disabled = true;
    btn.textContent = 'Detecting...';
    try {
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      formData.append('threshold', document.getElementById('detect-threshold')?.value || '0.5');
      const res = await fetch(`${API_BASE}/images/analyze/detect-objects`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Detection failed');
      const data = await res.json();
      const list = (data.objects || []).map(o => `<li>${o.label} (${(o.score * 100).toFixed(1)}%)</li>`).join('');
      document.getElementById('detect-result').innerHTML = `
        <div class="card" style="padding: 1rem; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 0.5rem;">
          <h3 style="font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;">Objects (${data.objects?.length || 0})</h3>
          <ul style="padding-left: 1.25rem;">${list || '<li>None detected</li>'}</ul>
        </div>
      `;
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Detect Objects';
    }
  }

  async handleSegment() {
    const fileInput = document.getElementById('segment-file');
    if (!fileInput?.files?.[0]) return showError('Select an image');
    const btn = document.getElementById('segment-btn');
    btn.disabled = true;
    btn.textContent = 'Segmenting...';
    try {
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      const res = await fetch(`${API_BASE}/images/analyze/segment`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Segmentation failed');
      const data = await res.json();
      const list = (data.segments || []).map(s => `<li>${s.label}</li>`).join('');
      document.getElementById('segment-result').innerHTML = `
        <div class="card" style="padding: 1rem; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 0.5rem;">
          <h3 style="font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;">Segments (${data.segments?.length || 0})</h3>
          <ul style="padding-left: 1.25rem;">${list || '<li>None detected</li>'}</ul>
        </div>
      `;
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Segment';
    }
  }

  handleLogout() {
    fetch(`${API_BASE}/auth/logout`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}) } }).catch(() => {});
    localStorage.removeItem('astrovox_access_token');
    localStorage.removeItem('astrovox_refresh_token');
    clearUser();
    window.location.href = '/login.html';
  }
}

function getUser() {
  try {
    const raw = localStorage.getItem('astrovox_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function clearUser() {
  localStorage.removeItem('astrovox_user');
}

function initRouter() {
  window.addEventListener('hashchange', () => {
    if (window.app) {
      window.app._checkAuthAndRoute();
    }
  });

  document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
  });
}

window.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  if (path === '/image-ai.html') {
    const app = document.getElementById('app');
    if (app) {
      const token = getToken();
      if (!token) {
        window.location.href = '/login.html';
        return;
      }
      const imgApp = new ImageAIApp();
    }
  } else {
    initRouter();
  }
});
