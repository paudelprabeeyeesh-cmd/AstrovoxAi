// Firefox background script
const API_BASE = 'https://api.astrovox.ai/v1'

browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'CHAT') {
    handleChat(message.payload).then(sendResponse).catch(error => sendResponse({ error: error.message }))
    return true
  }
  if (message.type === 'EXPLAIN') {
    handleExplain(message.payload).then(sendResponse).catch(error => sendResponse({ error: error.message }))
    return true
  }
  if (message.type === 'SUMMARIZE') {
    handleSummarize(message.payload).then(sendResponse).catch(error => sendResponse({ error: error.message }))
    return true
  }
})

async function handleChat(payload) {
  const response = await fetch(`${API_BASE}/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${payload.apiKey || ''}` },
    body: JSON.stringify({ message: payload.text, context: payload.context })
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

async function handleExplain(payload) {
  const response = await fetch(`${API_BASE}/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: payload.text })
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

async function handleSummarize(payload) {
  const response = await fetch(`${API_BASE}/summarize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: payload.text, max_length: payload.maxLength || 200 })
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}
