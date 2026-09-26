// Frontend Platform - Code Agent UI
const CodeAgentUI = {
  _container: null,
  _apiBase: null,
  _repoPath: '',
  _activeTab: 'files',
  _files: [],
  _symbols: [],
  _analysis: null,
  _isIndexing: false,

  init(container, apiBase, repoPath) {
    if (!container) return null;
    this._container = container;
    this._apiBase = apiBase || window.__API_BASE__ || 'http://localhost:8000';
    this._repoPath = repoPath || '.';
    this._render();
    this._bindEvents();
    return this;
  },

  async indexRepo() {
    if (this._isIndexing) return;
    this._isIndexing = true;
    this._setStatus('Indexing repository...');
    try {
      const res = await fetch(`${this._apiBase}/coding/index`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({repo_path: this._repoPath}),
      });
      const data = await res.json();
      this._analysis = data;
      this._setStatus(`Indexed ${data.files_indexed || 0} files, ${data.symbols_found || 0} symbols`);
    } catch (e) {
      this._setStatus('Indexing failed: ' + e.message);
    } finally {
      this._isIndexing = false;
    }
  },

  async searchSymbol(query) {
    if (!query) return [];
    try {
      const res = await fetch(`${this._apiBase}/coding/symbol?symbol=${encodeURIComponent(query)}&repo_path=${encodeURIComponent(this._repoPath)}`);
      const data = await res.json();
      this._symbols = data.references || [];
      this._renderSymbols();
      return this._symbols;
    } catch (e) {
      this._setStatus('Symbol search failed');
      return [];
    }
  },

  async readFile(path, offset, limit) {
    try {
      const url = `${this._apiBase}/coding/file?file_path=${encodeURIComponent(path)}&repo_path=${encodeURIComponent(this._repoPath)}&offset=${offset || 1}&limit=${limit || 200}`;
      const res = await fetch(url);
      const data = await res.json();
      return data;
    } catch (e) {
      return {error: e.message};
    }
  },

  async editFile(path, oldStr, newStr) {
    try {
      const res = await fetch(`${this._apiBase}/coding/edit`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({file_path: path, old_string: oldStr, new_string: newStr, repo_path: this._repoPath}),
      });
      return await res.json();
    } catch (e) {
      return {success: false, error: e.message};
    }
  },

  async analyzeDeps() {
    try {
      const res = await fetch(`${this._apiBase}/coding/analyze`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({repo_path: this._repoPath}),
      });
      return await res.json();
    } catch (e) {
      return {error: e.message};
    }
  },

  async suggestRefactors(path) {
    try {
      const res = await fetch(`${this._apiBase}/coding/refactor`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({file_path: path, repo_path: this._repoPath}),
      });
      return await res.json();
    } catch (e) {
      return {error: e.message};
    }
  },

  async generateTests(path, symbol) {
    try {
      const res = await fetch(`${this._apiBase}/coding/tests`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({file_path: path, symbol_name: symbol, repo_path: this._repoPath}),
      });
      return await res.json();
    } catch (e) {
      return {error: e.message};
    }
  },

  async scanBugs(path) {
    try {
      const res = await fetch(`${this._apiBase}/coding/bugs`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({file_path: path, repo_path: this._repoPath}),
      });
      return await res.json();
    } catch (e) {
      return {error: e.message};
    }
  },

  async review(path, diff) {
    try {
      const body = {repo_path: this._repoPath};
      if (diff) body.diff = diff;
      else body.file_path = path;
      const res = await fetch(`${this._apiBase}/coding/review`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
      });
      return await res.json();
    } catch (e) {
      return {error: e.message};
    }
  },

  async generateDocs(path) {
    try {
      const res = await fetch(`${this._apiBase}/coding/docs`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({file_path: path, repo_path: this._repoPath}),
      });
      return await res.json();
    } catch (e) {
      return {error: e.message};
    }
  },

  async inferApi(files, language) {
    try {
      const res = await fetch(`${this._apiBase}/coding/api`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({file_paths: files, repo_path: this._repoPath, language: language || 'python'}),
      });
      return await res.json();
    } catch (e) {
      return {error: e.message};
    }
  },

  async architectureAnalysis() {
    try {
      const res = await fetch(`${this._apiBase}/coding/architecture`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({repo_path: this._repoPath}),
      });
      return await res.json();
    } catch (e) {
      return {error: e.message};
    }
  },

  async runTask(task, target) {
    try {
      const res = await fetch(`${this._apiBase}/coding/task`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({task, target, repo_path: this._repoPath}),
      });
      return await res.json();
    } catch (e) {
      return {error: e.message};
    }
  },

  _render() {
    if (!this._container) return;
    this._container.innerHTML = `
      <div class="code-agent-panel">
        <div class="code-agent-header">
          <h3>Coding Agent</h3>
          <div class="code-agent-controls">
            <input type="text" id="ca-repo-path" value="${this._repoPath}" placeholder="Repository path" />
            <button id="ca-index">Index</button>
            <button id="ca-analyze">Analyze</button>
          </div>
        </div>
        <div class="code-agent-tabs">
          <button data-tab="files" class="active">Files</button>
          <button data-tab="symbols">Symbols</button>
          <button data-tab="tools">Tools</button>
          <button data-tab="output">Output</button>
        </div>
        <div class="code-agent-body">
          <div class="code-agent-tab-panel" data-panel="files">
            <div class="code-agent-search">
              <input type="text" id="ca-search" placeholder="Search symbols..." />
              <button id="ca-search-btn">Search</button>
            </div>
            <div class="code-agent-file-list" id="ca-file-list"></div>
          </div>
          <div class="code-agent-tab-panel hidden" data-panel="symbols">
            <div class="code-agent-symbol-list" id="ca-symbol-list"></div>
          </div>
          <div class="code-agent-tab-panel hidden" data-panel="tools">
            <div class="code-agent-tools">
              <div class="tool-group">
                <h4>Refactor</h4>
                <input type="text" id="ca-refactor-path" placeholder="File path" />
                <button id="ca-refactor-btn">Suggest</button>
                <pre id="ca-refactor-output"></pre>
              </div>
              <div class="tool-group">
                <h4>Tests</h4>
                <input type="text" id="ca-test-path" placeholder="File path" />
                <input type="text" id="ca-test-symbol" placeholder="Symbol name" />
                <button id="ca-test-btn">Generate</button>
                <pre id="ca-test-output"></pre>
              </div>
              <div class="tool-group">
                <h4>Bugs</h4>
                <input type="text" id="ca-bug-path" placeholder="File path" />
                <button id="ca-bug-btn">Scan</button>
                <pre id="ca-bug-output"></pre>
              </div>
              <div class="tool-group">
                <h4>Docs</h4>
                <input type="text" id="ca-doc-path" placeholder="File path" />
                <button id="ca-doc-btn">Generate</button>
                <pre id="ca-doc-output"></pre>
              </div>
              <div class="tool-group">
                <h4>Review</h4>
                <input type="text" id="ca-review-path" placeholder="File path" />
                <button id="ca-review-btn">Review</button>
                <pre id="ca-review-output"></pre>
              </div>
              <div class="tool-group">
                <h4>Architecture</h4>
                <button id="ca-arch-btn">Analyze</button>
                <pre id="ca-arch-output"></pre>
              </div>
            </div>
          </div>
          <div class="code-agent-tab-panel hidden" data-panel="output">
            <div class="code-agent-output" id="ca-output"></div>
          </div>
        </div>
      </div>
    `;
  },

  _bindEvents() {
    const container = this._container;
    if (!container) return;
    container.querySelector('#ca-index')?.addEventListener('click', () => {
      this._repoPath = container.querySelector('#ca-repo-path')?.value || '.';
      this.indexRepo();
    });
    container.querySelector('#ca-search-btn')?.addEventListener('click', () => {
      const q = container.querySelector('#ca-search')?.value || '';
      this.searchSymbol(q);
    });
    container.querySelector('#ca-analyze')?.addEventListener('click', async () => {
      const data = await this.analyzeDeps();
      this._renderOutput(data);
    });
    container.querySelector('#ca-refactor-btn')?.addEventListener('click', async () => {
      const path = container.querySelector('#ca-refactor-path')?.value || '';
      const data = await this.suggestRefactors(path);
      this._showOutput('ca-refactor-output', data);
    });
    container.querySelector('#ca-test-btn')?.addEventListener('click', async () => {
      const path = container.querySelector('#ca-test-path')?.value || '';
      const symbol = container.querySelector('#ca-test-symbol')?.value || '';
      const data = await this.generateTests(path, symbol);
      this._showOutput('ca-test-output', data);
    });
    container.querySelector('#ca-bug-btn')?.addEventListener('click', async () => {
      const path = container.querySelector('#ca-bug-path')?.value || '';
      const data = await this.scanBugs(path);
      this._showOutput('ca-bug-output', data);
    });
    container.querySelector('#ca-doc-btn')?.addEventListener('click', async () => {
      const path = container.querySelector('#ca-doc-path')?.value || '';
      const data = await this.generateDocs(path);
      this._showOutput('ca-doc-output', data);
    });
    container.querySelector('#ca-review-btn')?.addEventListener('click', async () => {
      const path = container.querySelector('#ca-review-path')?.value || '';
      const data = await this.review(path);
      this._showOutput('ca-review-output', data);
    });
    container.querySelector('#ca-arch-btn')?.addEventListener('click', async () => {
      const data = await this.architectureAnalysis();
      this._showOutput('ca-arch-output', data);
    });
    container.querySelectorAll('.code-agent-tabs button').forEach(btn => {
      btn.addEventListener('click', () => {
        container.querySelectorAll('.code-agent-tabs button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        this._activeTab = tab;
        container.querySelectorAll('.code-agent-tab-panel').forEach(p => p.classList.toggle('hidden', p.dataset.panel !== tab));
      });
    });
  },

  _renderSymbols() {
    const el = this._container?.querySelector('#ca-symbol-list');
    if (!el) return;
    el.innerHTML = this._symbols.map(s => `<div class="symbol-item"><strong>${s.name}</strong> <span class="symbol-kind">${s.kind}</span> <span class="symbol-file">${s.file}:${s.line}</span></div>`).join('') || '<p>No symbols found</p>';
  },

  _showOutput(id, data) {
    const el = this._container?.querySelector(`#${id}`);
    if (el) el.textContent = JSON.stringify(data, null, 2);
  },

  _renderOutput(data) {
    const el = this._container?.querySelector('#ca-output');
    if (el) el.textContent = JSON.stringify(data, null, 2);
  },

  _setStatus(msg) {
    const el = this._container?.querySelector('.code-agent-status');
    if (el) el.textContent = msg;
    console.log('[CodeAgent]', msg);
  },
};
