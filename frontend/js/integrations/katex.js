const KaTeX = {
  _loaded: false,

  async render(container, latex) {
    if (!container) return;

    try {
      if (!this._loaded) {
        await this._loadStylesheet('https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.css');
        await this._loadScript('https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.js');
        this._loaded = true;
      }

      if (typeof katex === 'undefined') {
        container.innerHTML = `<code>${latex}</code>`;
        return;
      }

      container.innerHTML = '';
      katex.render(latex, container, {
        throwOnError: false,
        displayMode: false,
        strict: false,
      });
    } catch (err) {
      container.innerHTML = `<code>${latex}</code>`;
    }
  },

  async renderDisplay(container, latex) {
    if (!container) return;

    try {
      if (!this._loaded) {
        await this._loadStylesheet('https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.css');
        await this._loadScript('https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.js');
        this._loaded = true;
      }

      if (typeof katex === 'undefined') {
        container.innerHTML = `<pre>${latex}</pre>`;
        return;
      }

      container.innerHTML = '';
      katex.render(latex, container, {
        throwOnError: false,
        displayMode: true,
        strict: false,
      });
    } catch (err) {
      container.innerHTML = `<pre>${latex}</pre>`;
    }
  },

  _loadStylesheet(href) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`link[href="${href}"]`)) {
        resolve();
        return;
      }
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;
      link.onload = resolve;
      link.onerror = reject;
      document.head.appendChild(link);
    });
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

window.KaTeX = KaTeX;
