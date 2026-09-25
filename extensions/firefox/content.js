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

  function getInitials(name) {
    if (!name) return 'U'
    const parts = name.trim().split(/\s+/)
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    }
    return name.slice(0, 2).toUpperCase()
  }

  function formatRelativeTime(date) {
    if (!date) return ''
    const diff = Math.floor((Date.now() - new Date(date).getTime()) / 1000)
    if (diff < 60) return 'Just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return `${Math.floor(diff / 86400)}d ago`
  }

  injectStyles()
  document.addEventListener('mouseup', () => {
    setTimeout(handleSelection, 100)
  })
})()
