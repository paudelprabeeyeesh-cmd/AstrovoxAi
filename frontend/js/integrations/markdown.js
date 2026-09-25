// Frontend Platform - Group 3: Markdown/Mermaid/KaTeX/Monaco integrations
const Markdown = {
  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },

  _parseInlineMarkdown(text) {
    let html = this._escapeHtml(text);

    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    return html;
  },

  render(text) {
    if (!text) return '';

    const lines = text.split('\n');
    const html = [];
    let inCodeBlock = false;
    let codeContent = [];
    let codeLang = '';

    for (const line of lines) {
      const trimmed = line.trim();

      if (trimmed.startsWith('```')) {
        if (!inCodeBlock) {
          if (codeContent.length) html.push(codeContent.join('\n'));
          codeContent = [];
          codeLang = trimmed.slice(3).trim();
          inCodeBlock = true;
          continue;
        } else {
          inCodeBlock = false;
          const escaped = this._escapeHtml(codeContent.join('\n'));
          html.push(`<pre><code class="language-${codeLang}">${escaped}</code></pre>`);
          codeContent = [];
          codeLang = '';
          continue;
        }
      }

      if (inCodeBlock) {
        codeContent.push(line);
        continue;
      }

      if (trimmed.startsWith('# ')) {
        html.push(`<h1>${this._parseInlineMarkdown(trimmed.slice(2))}</h1>`);
      } else if (trimmed.startsWith('## ')) {
        html.push(`<h2>${this._parseInlineMarkdown(trimmed.slice(3))}</h2>`);
      } else if (trimmed.startsWith('### ')) {
        html.push(`<h3>${this._parseInlineMarkdown(trimmed.slice(4))}</h3>`);
      } else if (trimmed.startsWith('- ')) {
        html.push(`<li>${this._parseInlineMarkdown(trimmed.slice(2))}</li>`);
      } else if (trimmed === '') {
        html.push('<br>');
      } else {
        html.push(`<p>${this._parseInlineMarkdown(trimmed)}</p>`);
      }
    }

    if (codeContent.length) {
      html.push(`<pre><code>${this._escapeHtml(codeContent.join('\n'))}</code></pre>`);
    }

    return html.join('\n');
  },
};

window.Markdown = Markdown;
