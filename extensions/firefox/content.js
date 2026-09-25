// Firefox content script
(function() {
  'use strict'

  const API_BASE = 'https://api.astrovox.ai/v1'

  function injectStyles() {
    const style = document.createElement('style')
    style.textContent = `
      .astrovox-highlight {
        background-color: rgba(6, 182, 212, 0.1);
        border-bottom: 2px solid #06b6d4;
        cursor: pointer;
      }
    `
    document.head.appendChild(style)
  }

  function handleSelection() {
    const selection = window.getSelection()
    const text = selection.toString().trim()
    if (!text) return

    browser.runtime.sendMessage({
      type: 'CONTEXT_SELECTION',
      payload: { text, url: window.location.href }
    }).catch(() => {})
  }

  injectStyles()
  document.addEventListener('mouseup', () => {
    setTimeout(handleSelection, 100)
  })
})()
