// Frontend Platform - Group 3: Monaco code editor integration
const Monaco = {
  _editor: null,
  _container: null,
  _decorations: [],
  _options: {
    theme: 'vs-dark',
    language: 'javascript',
    readOnly: false,
    minimap: { enabled: false },
    fontSize: 14,
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
    automaticLayout: true,
    tabSize: 2,
    wordWrap: 'on',
    padding: { top: 16 },
    overviewRulerBorder: false,
    overviewRulerLanes: 0,
  },

  async load() {
    if (typeof monaco !== 'undefined') return monaco;

    await this._loadScript('https://cdn.jsdelivr.net/npm/monaco-editor@0.45/min/vs/loader.js');

    return new Promise((resolve) => {
      require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45/min/vs' } });
      require(['vs/editor/editor.main'], () => {
        this._defineTheme();
        resolve(monaco);
      });
    });
  },

  _defineTheme() {
    if (typeof monaco === 'undefined') return;

    monaco.editor.defineTheme('astrovox-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: 'comment', foreground: '64748b', fontStyle: 'italic' },
        { token: 'keyword', foreground: '0ea5e9' },
        { token: 'string', foreground: '22c55e' },
        { token: 'number', foreground: 'f59e0b' },
        { token: 'type', foreground: '94a3b8' },
        { token: 'function', foreground: 'f1f5f9' },
        { token: 'variable', foreground: 'f1f5f9' },
      ],
      colors: {
        'editor.background': '#0f172a',
        'editor.foreground': '#f1f5f9',
        'editor.lineHighlightBackground': '#1e293b',
        'editor.selectionBackground': '#334155',
        'editorCursor.foreground': '#0ea5e9',
        'editorLineNumber.foreground': '#64748b',
        'editorLineNumber.activeForeground': '#94a3b8',
      },
    });
  },

  async create(container, options = {}) {
    const editor = await this.load();
    const mergedOptions = { ...this._options, ...options };
    this._container = container;

    if (this._editor) {
      this._editor.dispose();
    }

    this._editor = editor.create(container, mergedOptions);
    return this._editor;
  },

  getValue() {
    return this._editor?.getValue() ?? '';
  },

  setValue(value) {
    if (this._editor) {
      this._editor.setValue(value);
    }
  },

  setLanguage(language) {
    if (this._editor) {
      const model = this._editor.getModel();
      if (model) {
        monaco.editor.setModelLanguage(model, language);
      }
    }
  },

  setTheme(theme) {
    if (typeof monaco !== 'undefined') {
      monaco.editor.setTheme(theme === 'light' ? 'vs' : 'astrovox-dark');
    }
  },

  setReadOnly(readOnly) {
    if (this._editor) {
      this._editor.updateOptions({ readOnly });
    }
  },

  addDecorations(decorations) {
    if (!this._editor) return [];
    const model = this._editor.getModel();
    if (!model) return [];

    const monacoDecorations = decorations.map(d => ({
      range: new monaco.Range(d.line, d.startCol, d.line, d.endCol),
      options: {
        className: d.className || '',
        glyphMarginClassName: d.glyphClass || '',
        hoverMessage: d.hoverMessage ? { value: d.hoverMessage } : undefined,
        afterContentClassName: d.afterClass || '',
      },
    }));

    this._decorations = this._editor.deltaDecorations(this._decorations, monacoDecorations);
    return this._decorations;
  },

  clearDecorations() {
    if (this._editor) {
      this._editor.deltaDecorations(this._decorations, []);
      this._decorations = [];
    }
  },

  onDidChangeContent(callback) {
    if (this._editor) {
      this._editor.onDidChangeModelContent(callback);
    }
  },

  focus() {
    this._editor?.focus();
  },

  dispose() {
    this._editor?.dispose();
    this._editor = null;
    this._container = null;
    this._decorations = [];
  },

  _loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve();
        return;
      }
      const script = document.createElement('script');
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  },
};

window.Monaco = Monaco;
