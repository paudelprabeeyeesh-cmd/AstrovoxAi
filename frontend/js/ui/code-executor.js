// Frontend Platform - Group 10: Code execution UI with language tabs and output panels
const CodeExecutor = {
  _container: null,
  _tabs = [],
  _activeTab = null,
  _output = null,
  _isRunning = false,

  create(container, options = {}) {
    if (!container) return null;

    this._container = container;
    this._tabs = options.tabs || [];
    this._activeTab = this._tabs[0] || null;
    this._isRunning = false;

    container.innerHTML = '';
    this._render();
    return this;
  },

  addTab(tab) {
    this._tabs.push({
      id: tab.id || crypto.randomUUID(),
      label: tab.label,
      language: tab.language || 'javascript',
      code: tab.code || '',
      readOnly: tab.readOnly || false,
    });
    this._renderTabs();
  },

  switchTab(id) {
    this._activeTab = this._tabs.find(t => t.id === id) || this._tabs[0];
    this._renderTabs();
    this._renderEditor();
  },

  getCode() {
    const editor = this._container?.querySelector('.code-executor-editor');
    return editor?.value || '';
  },

  setCode(code) {
    const editor = this._container?.querySelector('.code-executor-editor');
    if (editor) editor.value = code;
  },

  async run() {
    if (this._isRunning) return;
    this._isRunning = true;
    this._showRunning();

    const code = this.getCode();
    const language = this._activeTab?.language || 'javascript';

    try {
      const result = await this._execute(code, language);
      this._showOutput(result);
    } catch (err) {
      this._showError(err.message);
    } finally {
      this._isRunning = false;
      this._hideRunning();
    }
  },

  clear() {
    const output = this._container?.querySelector('.code-executor-output');
    if (output) output.innerHTML = '';
  },

  async _execute(code, language) {
    const result = { stdout: '', stderr: '', exitCode: 0, executionTime: 0 };

    try {
      const startTime = Date.now();

      if (language === 'javascript' || language === 'js' || language === 'typescript' || language === 'ts') {
        const logs = [];
        const originalLog = console.log;
        const originalError = console.error;

        console.log = (...args) => {
          logs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a, null, 2) : String(a)).join(' '));
        };
        console.error = (...args) => {
          logs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a, null, 2) : String(a)).join(' '));
          result.stderr += logs.join('\n');
        };

        try {
          const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
          const fn = new AsyncFunction(code);
          await fn();
          result.stdout = logs.join('\n');
        } catch (err) {
          result.stderr += err.message + '\n';
          result.exitCode = 1;
        } finally {
          console.log = originalLog;
          console.error = originalError;
        }
      } else {
        result.stdout = `Execution of ${language} is not supported in browser.\nCode:\n${code.slice(0, 200)}`;
      }

      result.executionTime = Date.now() - startTime;
    } catch (err) {
      result.stderr += err.message + '\n';
      result.exitCode = 1;
    }

    return result;
  },

  _render() {
    if (!this._container) return;

    this._container.innerHTML = `
      <div class="code-executor">
        <div class="code-executor-header">
          <div class="code-executor-tabs" role="tablist"></div>
          <div class="code-executor-actions">
            <button class="btn btn-sm btn-secondary" id="code-executor-clear">Clear</button>
            <button class="btn btn-sm btn-primary" id="code-executor-run">▶ Run</button>
          </div>
        </div>
        <div class="code-executor-body"></div>
        <div class="code-executor-output"></div>
      </div>
    `;

    this._renderTabs();
    this._renderEditor();

    this._container.querySelector('#code-executor-run')?.addEventListener('click', () => this.run());
    this._container.querySelector('#code-executor-clear')?.addEventListener('click', () => this.clear());
  },

  _renderTabs() {
    const tabsEl = this._container?.querySelector('.code-executor-tabs');
    if (!tabsEl) return;

    tabsEl.innerHTML = this._tabs.map(tab => `
      <button class="code-executor-tab ${tab.id === this._activeTab?.id ? 'active' : ''}" role="tab" data-id="${tab.id}" aria-selected="${tab.id === this._activeTab?.id}">
        ${tab.label}
      </button>
    `).join('');

    tabsEl.querySelectorAll('.code-executor-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.switchTab(tab.dataset.id);
      });
    });
  },

  _renderEditor() {
    const bodyEl = this._container?.querySelector('.code-executor-body');
    if (!bodyEl) return;

    const tab = this._activeTab || this._tabs[0];
    if (!tab) {
      bodyEl.innerHTML = '';
      return;
    }

    bodyEl.innerHTML = `
      <div class="code-executor-editor-wrapper">
        <div class="code-executor-language-badge">${tab.language}</div>
        <textarea class="code-executor-editor" spellcheck="false" autocomplete="off" autocorrect="off" autocapitalize="off">${tab.code}</textarea>
      </div>
    `;
  },

  _showRunning() {
    const outputEl = this._container?.querySelector('.code-executor-output');
    if (outputEl) {
      outputEl.innerHTML = `<div class="code-executor-running"><div class="spinner spinner-sm"></div> Running...</div>`;
    }
  },

  _hideRunning() {
    const runningEl = this._container?.querySelector('.code-executor-running');
    runningEl?.remove();
  },

  _showOutput(result) {
    const outputEl = this._container?.querySelector('.code-executor-output');
    if (!outputEl) return;

    const hasOutput = result.stdout || result.stderr;
    const statusClass = result.exitCode === 0 ? 'success' : 'error';

    outputEl.innerHTML = hasOutput ? `
      <div class="code-executor-result code-executor-result-${statusClass}">
        <div class="code-executor-result-header">
          <span>${result.exitCode === 0 ? 'Success' : 'Error'}</span>
          <span>${result.executionTime}ms</span>
        </div>
        ${result.stdout ? `<pre class="code-executor-stdout">${result.stdout}</pre>` : ''}
        ${result.stderr ? `<pre class="code-executor-stderr">${result.stderr}</pre>` : ''}
      </div>
    ` : '';
  },

  _showError(message) {
    const outputEl = this._container?.querySelector('.code-executor-output');
    if (outputEl) {
      outputEl.innerHTML = `<div class="code-executor-result code-executor-result-error"><pre>${message}</pre></div>`;
    }
  },
};

window.CodeExecutor = CodeExecutor;
