// Safari background script
const API_BASE = 'https://api.astrovox.ai/v1'

safari.application.addEventListener('message', (event) => {
  if (event.name === 'CHAT') {
    handleChat(event.message).then(response => {
      event.target.page.dispatchMessage('CHAT_RESPONSE', response)
    }).catch(error => {
      event.target.page.dispatchMessage('CHAT_ERROR', { error: error.message })
    })
  }
})

async function handleChat(payload) {
  const response = await fetch(`${API_BASE}/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: payload.text })
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}
