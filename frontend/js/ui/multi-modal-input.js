// Frontend Platform - Group 11: Multi-modal input: voice, camera, screen share
const MultiModalInput = {
  _container: null,
  _modes = ['text', 'voice', 'camera', 'screen'],
  _activeMode = 'text',
  _stream = null,
  _mediaRecorder = null,
  _audioChunks = [],
  _screenStream = null,

  create(container, options = {}) {
    if (!container) return null;

    this._container = container;
    this._onSubmit = options.onSubmit || (() => {});
    this._placeholder = options.placeholder || 'Send a message...';

    container.innerHTML = '';
    this._render();
    return this;
  },

  _render() {
    if (!this._container) return;

    this._container.innerHTML = `
      <div class="multimodal-input">
        <div class="multimodal-input-toolbar">
          ${this._modes.map(mode => `
            <button class="multimodal-tool-btn ${mode === this._activeMode ? 'active' : ''}" data-mode="${mode}" aria-label="${mode}" title="${mode}">
              ${this._getModeIcon(mode)}
            </button>
          `).join('')}
        </div>
        <div class="multimodal-input-body">
          <textarea class="multimodal-textarea" placeholder="${this._placeholder}" rows="1"></textarea>
          <div class="multimodal-input-actions">
            <button class="btn btn-sm btn-secondary multimodal-record-btn" aria-label="Record audio">
              🎤
            </button>
            <button class="btn btn-sm btn-primary multimodal-submit-btn">
              Send
            </button>
          </div>
        </div>
        <div class="multimodal-preview"></div>
        <div class="multimodal-status"></div>
      </div>
    `;

    this._bindEvents();
  },

  _bindEvents() {
    const textarea = this._container?.querySelector('.multimodal-textarea');
    const submitBtn = this._container?.querySelector('.multimodal-submit-btn');
    const recordBtn = this._container?.querySelector('.multimodal-record-btn');
    const toolBtns = this._container?.querySelectorAll('.multimodal-tool-btn');

    submitBtn?.addEventListener('click', () => this._handleSubmit());
    recordBtn?.addEventListener('click', () => this._toggleRecording());
    textarea?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this._handleSubmit();
      }
    });

    toolBtns?.forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.dataset.mode;
        this.setMode(mode);
      });
    });
  },

  _getModeIcon(mode) {
    const icons = {
      text: '⌨',
      voice: '🎤',
      camera: '📷',
      screen: '🖥',
    };
    return icons[mode] || mode;
  },

  setMode(mode) {
    if (!this._modes.includes(mode)) return;

    this._activeMode = mode;
    this._stopAllMedia();

    const toolBtns = this._container?.querySelectorAll('.multimodal-tool-btn');
    toolBtns?.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    const textarea = this._container?.querySelector('.multimodal-textarea');
    const preview = this._container?.querySelector('.multimodal-preview');

    if (mode === 'text') {
      textarea?.removeAttribute('disabled');
      textarea?.focus();
    } else {
      textarea?.setAttribute('disabled', 'true');
      this._activateMode(mode);
    }

    if (mode !== 'text') {
      preview.innerHTML = `<div class="multimodal-mode-indicator">${mode} mode active</div>`;
    } else {
      preview.innerHTML = '';
    }
  },

  async _activateMode(mode) {
    const statusEl = this._container?.querySelector('.multimodal-status');

    if (mode === 'voice') {
      statusEl.innerHTML = '<div class="multimodal-listening">Listening...</div>';
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this._startRecording(stream);
      } catch (err) {
        statusEl.innerHTML = `<div class="multimodal-error">Microphone access denied</div>`;
      }
    } else if (mode === 'camera') {
      statusEl.innerHTML = '<div class="multimodal-capturing">Camera active</div>';
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        this._showCameraPreview(stream);
      } catch (err) {
        statusEl.innerHTML = `<div class="multimodal-error">Camera access denied</div>`;
      }
    } else if (mode === 'screen') {
      statusEl.innerHTML = '<div class="multimodal-sharing">Screen sharing active</div>';
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        this._showScreenPreview(stream);
      } catch (err) {
        statusEl.innerHTML = `<div class="multimodal-error">Screen share denied</div>`;
      }
    }
  },

  _startRecording(stream) {
    this._audioChunks = [];
    this._mediaRecorder = new MediaRecorder(stream);

    this._mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) this._audioChunks.push(e.data);
    };

    this._mediaRecorder.onstop = () => {
      const blob = new Blob(this._audioChunks, { type: 'audio/webm' });
      this._handleAudioBlob(blob);
      stream.getTracks().forEach(track => track.stop());
    };

    this._mediaRecorder.start();
  },

  _stopRecording() {
    if (this._mediaRecorder && this._mediaRecorder.state !== 'inactive') {
      this._mediaRecorder.stop();
    }
  },

  async _handleAudioBlob(blob) {
    const statusEl = this._container?.querySelector('.multimodal-status');
    statusEl.innerHTML = '<div class="multimodal-processing">Processing audio...</div>';

    try {
      const formData = new FormData();
      formData.append('audio', blob, 'recording.webm');

      const response = await fetch('/api/multimodal/transcribe', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        const textarea = this._container?.querySelector('.multimodal-textarea');
        if (textarea && data.text) {
          textarea.value = data.text;
        }
        statusEl.innerHTML = '';
      } else {
        statusEl.innerHTML = '<div class="multimodal-error">Transcription failed</div>';
      }
    } catch (err) {
      statusEl.innerHTML = `<div class="multimodal-error">${err.message}</div>`;
    }
  },

  _showCameraPreview(stream) {
    const preview = this._container?.querySelector('.multimodal-preview');
    if (!preview) return;

    const video = document.createElement('video');
    video.srcObject = stream;
    video.autoplay = true;
    video.playsInline = true;
    video.className = 'multimodal-video-preview';
    preview.innerHTML = '';
    preview.appendChild(video);
  },

  _showScreenPreview(stream) {
    const preview = this._container?.querySelector('.multimodal-preview');
    if (!preview) return;

    const video = document.createElement('video');
    video.srcObject = stream;
    video.autoplay = true;
    video.playsInline = true;
    video.className = 'multimodal-video-preview';
    preview.innerHTML = '';
    preview.appendChild(video);
  },

  _toggleRecording() {
    if (this._mediaRecorder && this._mediaRecorder.state === 'recording') {
      this._stopRecording();
    } else {
      this._stopAllMedia();
      this._startRecording();
    }
  },

  _handleSubmit() {
    const textarea = this._container?.querySelector('.multimodal-textarea');
    const text = textarea?.value?.trim();
    if (text) {
      this._onSubmit(text);
      if (textarea) textarea.value = '';
    }
  },

  _stopAllMedia() {
    if (this._mediaRecorder && this._mediaRecorder.state !== 'inactive') {
      this._mediaRecorder.stop();
    }

    if (this._screenStream) {
      this._screenStream.getTracks().forEach(track => track.stop());
      this._screenStream = null;
    }

    const preview = this._container?.querySelector('.multimodal-preview');
    if (preview) {
      const video = preview.querySelector('video');
      if (video && video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
      }
      preview.innerHTML = '';
    }
  },

  getMode() {
    return this._activeMode;
  },
};

window.MultiModalInput = MultiModalInput;
