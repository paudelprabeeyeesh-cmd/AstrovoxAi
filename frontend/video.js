(function () {
  'use strict';

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

  async function apiFetch(endpoint, options = {}) {
    let token = getToken();
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    };

    const resp = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    if (resp.status === 401) {
      try {
        const refresh = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: localStorage.getItem('astrovox_refresh_token') }),
        });
        if (refresh.ok) {
          const data = await refresh.json();
          localStorage.setItem('astrovox_access_token', data.access_token);
          headers.Authorization = `Bearer ${data.access_token}`;
          return fetch(`${API_BASE}${endpoint}`, { ...options, headers }).then(r => handleResponse(r));
        }
      } catch {
        // fall through
      }
      showError('Session expired. Please log in again.');
      setTimeout(() => { window.location.href = '/login'; }, 2000);
      throw new Error('Unauthorized');
    }
    return handleResponse(resp);
  }

  async function handleResponse(resp) {
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(err.detail || err.message || `HTTP ${resp.status}`);
    }
    return resp.json();
  }

  async function uploadFile(file) {
    const token = getToken();
    const form = new FormData();
    form.append('file', file);
    const resp = await fetch(`${API_BASE}/video/upload`, {
      method: 'POST',
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: form,
    });
    return handleResponse(resp);
  }

  const app = {
    async textToVideo() {
      const prompt = document.getElementById('ttv-prompt').value.trim();
      if (!prompt) { showError('Prompt is required'); return; }
      const duration = parseFloat(document.getElementById('ttv-duration').value) || 4;
      const width = parseInt(document.getElementById('ttv-width').value, 10) || 1024;
      const height = parseInt(document.getElementById('ttv-height').value, 10) || 576;
      const fps = parseInt(document.getElementById('ttv-fps').value, 10) || 24;
      const imageBase64 = document.getElementById('ttv-image').value.trim() || undefined;
      const resultEl = document.getElementById('ttv-result');
      resultEl.innerHTML = '<p class="text-secondary">Generating video...</p>';
      try {
        const data = await apiFetch('/video/text-to-video', {
          method: 'POST',
          body: JSON.stringify({ prompt, image_base64: imageBase64, duration_seconds: duration, width, height, fps }),
        });
        const videos = data.videos || [];
        if (!videos.length) {
          resultEl.innerHTML = '<p class="text-secondary">No video generated. Check backend configuration.</p>';
          return;
        }
        let html = '<p><strong>Generated:</strong></p>';
        videos.forEach((v, idx) => {
          html += `<div><strong>Video ${idx + 1}</strong> — ${v.width}x${v.height} @ ${v.fps}fps, ${v.duration_seconds.toFixed(1)}s, model=${v.model}`;
          if (v.url) {
            if (v.url.startsWith('data:image/gif')) {
              html += `<br><img src="${v.url}" alt="generated video">`;
            } else {
              html += `<br><a href="${v.url}" target="_blank">Download Video</a>`;
            }
          }
          if (v.seed) html += `<br>Seed: ${v.seed}`;
          html += '</div>';
        });
        resultEl.innerHTML = html;
        showToast('Video generated successfully');
      } catch (err) {
        resultEl.innerHTML = `<p class="error">Error: ${err.message}</p>`;
        showError(err.message);
      }
    },

    async summarize() {
      const fileInput = document.getElementById('sum-file');
      const prompt = document.getElementById('sum-prompt').value.trim();
      const maxScenes = parseInt(document.getElementById('sum-max-scenes').value, 10) || 5;
      if (!fileInput.files.length) { showError('Please select a video file'); return; }
      const resultEl = document.getElementById('sum-result');
      resultEl.innerHTML = '<p class="text-secondary">Analyzing video...</p>';
      try {
        const form = new FormData();
        form.append('file', fileInput.files[0]);
        if (prompt) form.append('prompt', prompt);
        form.append('max_scenes', String(maxScenes));
        const token = getToken();
        const resp = await fetch(`${API_BASE}/video/summarize`, {
          method: 'POST',
          headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: form,
        });
        const data = await handleResponse(resp);
        let html = `<p><strong>Summary:</strong> ${data.summary || 'No summary available.'}</p>`;
        html += `<p><strong>Scenes:</strong> ${data.scene_count || 0} | <strong>Duration:</strong> ${(data.duration_seconds || 0).toFixed(1)}s</p>`;
        if (data.key_frames && data.key_frames.length) {
          html += '<div class="key-frames">';
          data.key_frames.forEach(kf => {
            if (kf.image_base64) {
              html += `<img src="data:image/jpeg;base64,${kf.image_base64}" alt="frame" style="max-width:160px;margin:0.25rem;">`;
            }
          });
          html += '</div>';
        }
        resultEl.innerHTML = html;
        showToast('Summarization complete');
      } catch (err) {
        resultEl.innerHTML = `<p class="error">Error: ${err.message}</p>`;
        showError(err.message);
      }
    },

    async detectScenes() {
      const fileInput = document.getElementById('scene-file');
      const threshold = parseFloat(document.getElementById('scene-threshold').value) || 0.3;
      const method = document.getElementById('scene-method').value || 'histogram';
      if (!fileInput.files.length) { showError('Please select a video file'); return; }
      const resultEl = document.getElementById('scene-result');
      resultEl.innerHTML = '<p class="text-secondary">Detecting scenes...</p>';
      try {
        const form = new FormData();
        form.append('file', fileInput.files[0]);
        form.append('threshold', String(threshold));
        form.append('method', method);
        const token = getToken();
        const resp = await fetch(`${API_BASE}/video/scene-detect`, {
          method: 'POST',
          headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: form,
        });
        const data = await handleResponse(resp);
        const scenes = data.scenes || [];
        let html = `<p><strong>Scenes found:</strong> ${scenes.length}</p>`;
        if (scenes.length) {
          html += '<ul class="scene-list">';
          scenes.slice(0, 50).forEach(s => {
            html += `<li><span>${(s.timestamp || 0).toFixed(2)}s</span><span>score=${(s.score || 0).toFixed(3)} ${s.method || ''}</span></li>`;
          });
          html += '</ul>';
        }
        resultEl.innerHTML = html;
        showToast(`Detected ${scenes.length} scenes`);
      } catch (err) {
        resultEl.innerHTML = `<p class="error">Error: ${err.message}</p>`;
        showError(err.message);
      }
    },

    async generateSubtitles() {
      const fileInput = document.getElementById('sub-file');
      const language = document.getElementById('sub-lang').value.trim() || undefined;
      const format = document.getElementById('sub-format').value || 'srt';
      if (!fileInput.files.length) { showError('Please select a video file'); return; }
      const resultEl = document.getElementById('sub-result');
      resultEl.innerHTML = '<p class="text-secondary">Generating subtitles...</p>';
      try {
        const form = new FormData();
        form.append('file', fileInput.files[0]);
        if (language) form.append('language', language);
        form.append('format', format);
        const token = getToken();
        const resp = await fetch(`${API_BASE}/video/subtitles`, {
          method: 'POST',
          headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: form,
        });
        const data = await handleResponse(resp);
        const segments = data.segments || [];
        let html = `<p><strong>Segments:</strong> ${segments.length} | <strong>Format:</strong> ${data.format || format}</p>`;
        if (data.content) {
          html += `<pre class="subtitle-preview">${escapeHtml(data.content)}</pre>`;
        } else {
          html += '<pre class="subtitle-preview">No subtitle content available.</pre>';
        }
        resultEl.innerHTML = html;
        showToast('Subtitles generated');
      } catch (err) {
        resultEl.innerHTML = `<p class="error">Error: ${err.message}</p>`;
        showError(err.message);
      }
    },

    async lipSync() {
      const videoInput = document.getElementById('ls-video');
      const audioInput = document.getElementById('ls-audio');
      const fps = parseInt(document.getElementById('ls-fps').value, 10) || 25;
      if (!videoInput.files.length || !audioInput.files.length) { showError('Please select both video and audio files'); return; }
      const resultEl = document.getElementById('ls-result');
      resultEl.innerHTML = '<p class="text-secondary">Synchronizing lips...</p>';
      try {
        const form = new FormData();
        form.append('video', videoInput.files[0]);
        form.append('audio', audioInput.files[0]);
        form.append('fps', String(fps));
        const token = getToken();
        const resp = await fetch(`${API_BASE}/video/lip-sync`, {
          method: 'POST',
          headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: form,
        });
        const data = await handleResponse(resp);
        let html = `<p><strong>Duration:</strong> ${(data.duration_seconds || 0).toFixed(1)}s | <strong>FPS:</strong> ${data.fps || fps} | <strong>Model:</strong> ${data.model || 'unknown'}</p>`;
        if (data.output_path) {
          html += `<p><strong>Output:</strong> ${escapeHtml(data.output_path)}</p>`;
        }
        if (data.timestamps && data.timestamps.length) {
          html += '<p><strong>Timestamps (first 10):</strong></p><ul class="scene-list">';
          data.timestamps.slice(0, 10).forEach(t => {
            html += `<li><span>${t.time.toFixed(2)}s</span><span>frame=${t.frame}</span></li>`;
          });
          html += '</ul>';
        }
        resultEl.innerHTML = html;
        showToast('Lip sync complete');
      } catch (err) {
        resultEl.innerHTML = `<p class="error">Error: ${err.message}</p>`;
        showError(err.message);
      }
    },

    async trackMotion() {
      const fileInput = document.getElementById('mt-file');
      const bboxInput = document.getElementById('mt-bbox').value.trim();
      if (!fileInput.files.length) { showError('Please select a video file'); return; }
      let initBbox = undefined;
      if (bboxInput) {
        try {
          initBbox = JSON.parse(bboxInput);
        } catch {
          showError('Invalid bounding box JSON');
          return;
        }
      }
      const resultEl = document.getElementById('mt-result');
      resultEl.innerHTML = '<p class="text-secondary">Tracking motion...</p>';
      try {
        const form = new FormData();
        form.append('file', fileInput.files[0]);
        if (initBbox) form.append('init_bbox', JSON.stringify(initBbox));
        const token = getToken();
        const resp = await fetch(`${API_BASE}/video/motion-track`, {
          method: 'POST',
          headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: form,
        });
        const data = await handleResponse(resp);
        if (data.objects && data.objects.length) {
          let html = `<p><strong>Objects tracked:</strong> ${data.objects.length}</p>`;
          data.objects.forEach((obj, idx) => {
            html += `<div><strong>Object ${obj.object_id}</strong> — ${obj.label}, ${obj.bbox_count} points</div>`;
          });
          resultEl.innerHTML = html;
        } else if (data.object_id !== undefined) {
          let html = `<p><strong>Object:</strong> ${data.object_id} — ${data.label}</p>`;
          html += `<p><strong>Bboxes:</strong> ${(data.bboxes || []).length}</p>`;
          if (data.trajectory && data.trajectory.length) {
            html += '<p><strong>Trajectory (first 10):</strong></p><ul class="scene-list">';
            data.trajectory.slice(0, 10).forEach(p => {
              html += `<li><span>x=${p.x.toFixed(1)}</span><span>y=${p.y.toFixed(1)}</span></li>`;
            });
            html += '</ul>';
          }
          resultEl.innerHTML = html;
        } else {
          resultEl.innerHTML = '<p class="text-secondary">No objects tracked.</p>';
        }
        showToast('Motion tracking complete');
      } catch (err) {
        resultEl.innerHTML = `<p class="error">Error: ${err.message}</p>`;
        showError(err.message);
      }
    },

    async interpolate() {
      const fileInput = document.getElementById('int-file');
      const multiplier = parseInt(document.getElementById('int-mult').value, 10) || 2;
      const method = document.getElementById('int-method').value || 'flow';
      if (!fileInput.files.length) { showError('Please select a video file'); return; }
      const resultEl = document.getElementById('int-result');
      resultEl.innerHTML = '<p class="text-secondary">Interpolating frames...</p>';
      try {
        const form = new FormData();
        form.append('file', fileInput.files[0]);
        form.append('multiplier', String(multiplier));
        form.append('method', method);
        const token = getToken();
        const resp = await fetch(`${API_BASE}/video/interpolate`, {
          method: 'POST',
          headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: form,
        });
        const data = await handleResponse(resp);
        let html = `<p><strong>Original FPS:</strong> ${(data.original_fps || 0).toFixed(1)} | <strong>Target FPS:</strong> ${(data.target_fps || 0).toFixed(1)}</p>`;
        html += `<p><strong>Output Frames:</strong> ${data.output_frames || 0} | <strong>Method:</strong> ${data.method || method}</p>`;
        if (data.output_path) {
          html += `<p><strong>Output:</strong> ${escapeHtml(data.output_path)}</p>`;
        }
        resultEl.innerHTML = html;
        showToast('Interpolation complete');
      } catch (err) {
        resultEl.innerHTML = `<p class="error">Error: ${err.message}</p>`;
        showError(err.message);
      }
    },

    logout() {
      try {
        localStorage.removeItem('astrovox_access_token');
        localStorage.removeItem('astrovox_refresh_token');
        localStorage.removeItem('astrovox_user');
      } catch {
        // ignore
      }
      window.location.href = '/login.html';
    },
  };

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.tab');
    const panels = document.querySelectorAll('.tab-panel');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        panels.forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        const target = document.getElementById(`tab-${tab.dataset.tab}`);
        if (target) target.classList.add('active');
      });
    });

    const user = (() => { try { return JSON.parse(localStorage.getItem('astrovox_user')); } catch { return null; } })();
    const nameEl = document.getElementById('nav-username');
    if (nameEl && user) {
      nameEl.textContent = user.name || user.email || 'User';
    }

    window.app = app;
  });
})();
