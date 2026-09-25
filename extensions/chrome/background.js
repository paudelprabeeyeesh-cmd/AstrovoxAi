// Background service worker for Chrome extension
const API_BASE = 'https://api.astrovox.ai/v1'

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'CHAT') {
    handleChat(message.payload)
      .then(sendResponse)
      .catch(error => sendResponse({ error: error.message }))
    return true
  }

  if (message.type === 'EXPLAIN') {
    handleExplain(message.payload)
      .then(sendResponse)
      .catch(error => sendResponse({ error: error.message }))
    return true
  }

  if (message.type === 'SUMMARIZE') {
    handleSummarize(message.payload)
      .then(sendResponse)
      .catch(error => sendResponse({ error: error.message }))
    return true
  }
})

async function handleChat(payload) {
  const response = await fetch(`${API_BASE}/chat/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${payload.apiKey}`
    },
    body: JSON.stringify({
      conversation_id: payload.conversationId || 'browser-' + Date.now(),
      message: payload.message,
      model: payload.model || 'gpt-4'
    })
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

async function handleExplain(payload) {
  const prompt = `Explain this code:\n\n${payload.code}`
  return handleChat({ ...payload, message: prompt })
}

async function handleSummarize(payload) {
  const prompt = `Summarize this page:\n\n${payload.content}`
  return handleChat({ ...payload, message: prompt })
}

chrome.contextMenus.create({
  id: 'astrovox-explain',
  title: 'Explain with Astrovox',
  contexts: ['selection']
})

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'astrovox-explain' && info.selectionText) {
    chrome.tabs.sendMessage(tab.id, {
      type: 'EXPLAIN_SELECTION',
      text: info.selectionText
    })
  }
})
