// Frontend Platform - Group 3: Mermaid diagram integration
const Mermaid = {
  _instances: new Map(),

  async render(container, code) {
    if (!container) return;
    container.innerHTML = '<div class="mermaid-loading">Loading diagram...</div>';

    try {
      if (typeof mermaid === 'undefined') {
        await this._loadScript('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js');
      }

      const id = 'mermaid-' + Date.now();
      const safeCode = code.replace(/"/g, '&quot;').replace(/'/g, '&#39;');

      container.innerHTML = `<div class="mermaid" id="${id}">${safeCode}</div>`;

      await mermaid.run({
        querySelector: `#${id}`,
        suppressErrors: true,
      });
    } catch (err) {
      container.innerHTML = `<pre class="mermaid-error">${err.message}</pre>`;
    }
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

window.Mermaid = Mermaid;
