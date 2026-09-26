/* RAG Panel module — chunking, search, citations, and knowledge management. */

const RAGPanel = (() => {
  const API_BASE = window.__API_BASE__ || 'http://localhost:8000';

  async function request(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`RAG request failed: ${res.status} ${text}`);
    }
    return res.json();
  }

  function $(selector, parent = document) {
    return parent.querySelector(selector);
  }

  function renderEmpty(container, message = 'No results') {
    container.innerHTML = `
      <div class="rag-empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div>${message}</div>
      </div>
    `;
  }

  function renderChunkCard(chunk, score = 0) {
    return `
      <div class="rag-chunk-card">
        <div class="rag-chunk-header">
          <span class="rag-chunk-id">${chunk.id || chunk.chunk_id || 'chunk'}</span>
          <span class="rag-chunk-score">score: ${(score || 0).toFixed(3)}</span>
        </div>
        <div class="rag-chunk-content">${escapeHtml(chunk.content || '')}</div>
        ${chunk.metadata && chunk.metadata.filename ? `<div class="rag-citation">Source: ${escapeHtml(chunk.metadata.filename)}</div>` : ''}
      </div>
    `;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  async function chunkDocument(text, documentId, strategy = 'semantic', chunkSize = 500, chunkOverlap = 50) {
    return request('/rag/chunk', {
      method: 'POST',
      body: JSON.stringify({ text, document_id: documentId, strategy, chunk_size: chunkSize, chunk_overlap: chunkOverlap }),
    });
  }

  async function embedText(text) {
    return request('/api/rag/embed', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  }

  async function hybridSearch(query, embedding = null, topK = 5) {
    return request('/api/rag/search', {
      method: 'POST',
      body: JSON.stringify({ query, embedding, top_k: topK }),
    });
  }

  async function multiQuerySearch(query, topK = 5) {
    return request('/api/rag/multi-query', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    });
  }

  async function compressContext(context, query, maxTokens = 4096) {
    return request('/api/rag/compress', {
      method: 'POST',
      body: JSON.stringify({ context, query, max_tokens: maxTokens }),
    });
  }

  async function generateCitation(title, authors, style = 'apa') {
    return request('/api/rag/citations', {
      method: 'POST',
      body: JSON.stringify({ title, authors, style }),
    });
  }

  function initChunkingForm(containerId, onChunked) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="rag-panel">
        <h2>Document Chunking</h2>
        <div class="rag-form-group">
          <label>Document ID</label>
          <input id="rag-doc-id" class="rag-input" placeholder="doc-001" />
        </div>
        <div class="rag-form-group">
          <label>Text</label>
          <textarea id="rag-text" class="rag-textarea" placeholder="Paste document text here..."></textarea>
        </div>
        <div class="rag-form-group">
          <label>Strategy</label>
          <select id="rag-strategy" class="rag-select">
            <option value="semantic" selected>Semantic</option>
            <option value="paragraph">Paragraph</option>
            <option value="sliding">Sliding Window</option>
            <option value="recursive">Recursive</option>
          </select>
        </div>
        <div style="display:flex; gap: 0.75rem;">
          <button id="rag-chunk-btn" class="rag-btn rag-btn-primary">Chunk Document</button>
          <button id="rag-clear-btn" class="rag-btn rag-btn-secondary">Clear</button>
        </div>
        <div id="rag-chunk-results" class="rag-chunk-list" style="margin-top: 1rem;"></div>
      </div>
    `;

    $('#rag-chunk-btn', container).addEventListener('click', async () => {
      const text = $('#rag-text', container).value;
      const documentId = $('#rag-doc-id', container).value || 'doc-' + Date.now();
      const strategy = $('#rag-strategy', container).value;
      const resultsContainer = $('#rag-chunk-results', container);

      if (!text.trim()) {
        resultsContainer.innerHTML = '<div class="rag-empty-state">Enter text to chunk</div>';
        return;
      }

      resultsContainer.innerHTML = '<div class="rag-empty-state">Chunking...</div>';
      try {
        const data = await chunkDocument(text, documentId, strategy);
        const chunks = data.chunks || data;
        if (Array.isArray(chunks)) {
          resultsContainer.innerHTML = chunks.map(c => renderChunkCard(c)).join('');
        } else {
          resultsContainer.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        }
        if (onChunked) onChunked(data);
      } catch (err) {
        resultsContainer.innerHTML = `<div class="rag-empty-state" style="color:#ef4444">${escapeHtml(err.message)}</div>`;
      }
    });

    $('#rag-clear-btn', container).addEventListener('click', () => {
      $('#rag-text', container).value = '';
      $('#rag-chunk-results', container).innerHTML = '';
    });
  }

  function initSearchForm(containerId, onResults) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="rag-panel">
        <h2>Hybrid Search</h2>
        <div class="rag-search-bar">
          <input id="rag-search-query" class="rag-input" placeholder="Search knowledge base..." />
          <input id="rag-search-topk" class="rag-input" type="number" value="5" min="1" max="20" style="width: 80px;" />
          <button id="rag-search-btn" class="rag-btn rag-btn-primary">Search</button>
        </div>
        <div class="rag-form-group">
          <label>Mode</label>
          <select id="rag-search-mode" class="rag-select">
            <option value="hybrid" selected>Hybrid</option>
            <option value="multi-query">Multi-Query</option>
          </select>
        </div>
        <div id="rag-search-results" class="rag-chunk-list"></div>
      </div>
    `;

    $('#rag-search-btn', container).addEventListener('click', async () => {
      const query = $('#rag-search-query', container).value;
      const topK = parseInt($('#rag-search-topk', container).value, 10) || 5;
      const mode = $('#rag-search-mode', container).value;
      const resultsContainer = $('#rag-search-results', container);

      if (!query.trim()) {
        resultsContainer.innerHTML = '<div class="rag-empty-state">Enter a query</div>';
        return;
      }

      resultsContainer.innerHTML = '<div class="rag-empty-state">Searching...</div>';
      try {
        const data = mode === 'multi-query' ? await multiQuerySearch(query, topK) : await hybridSearch(query, null, topK);
        const results = data.results || data;
        if (Array.isArray(results) && results.length) {
          resultsContainer.innerHTML = results.map(r => renderChunkCard(r, r.score)).join('');
        } else {
          renderEmpty(resultsContainer, 'No results found');
        }
        if (onResults) onResults(data);
      } catch (err) {
        resultsContainer.innerHTML = `<div class="rag-empty-state" style="color:#ef4444">${escapeHtml(err.message)}</div>`;
      }
    });
  }

  return {
    chunkDocument,
    embedText,
    hybridSearch,
    multiQuerySearch,
    compressContext,
    generateCitation,
    initChunkingForm,
    initSearchForm,
  };
})();
