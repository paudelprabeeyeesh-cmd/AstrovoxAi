document.getElementById('save').addEventListener('click', () => {
  const settings = {
    apiUrl: document.getElementById('apiUrl').value,
    apiKey: document.getElementById('apiKey').value,
    autoSuggest: document.getElementById('autoSuggest').checked,
    showHighlights: document.getElementById('showHighlights').checked
  }
  chrome.storage.local.set({ astrovoxSettings: settings }, () => {
    const status = document.getElementById('status')
    status.textContent = 'Settings saved'
    setTimeout(() => { status.textContent = '' }, 2000)
  })
})

chrome.storage.local.get(['astrovoxSettings'], (result) => {
  if (result.astrovoxSettings) {
    const s = result.astrovoxSettings
    document.getElementById('apiUrl').value = s.apiUrl || ''
    document.getElementById('apiKey').value = s.apiKey || ''
    document.getElementById('autoSuggest').checked = s.autoSuggest || false
    document.getElementById('showHighlights').checked = s.showHighlights !== false
  }
})
