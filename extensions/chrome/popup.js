document.getElementById('send').addEventListener('click', async () => {
  const input = document.getElementById('input')
  const response = document.getElementById('response')
  const text = input.value.trim()
  if (!text) return

  response.style.display = 'block'
  response.textContent = 'Thinking...'
  response.className = 'popup-response'

  try {
    const res = await chrome.runtime.sendMessage({ type: 'CHAT', payload: { message: text } })
    if (res.error) {
      response.textContent = res.error
      response.classList.add('popup-error')
    } else {
      response.textContent = res.content || JSON.stringify(res)
    }
  } catch (e) {
    response.textContent = 'Failed to send message'
    response.classList.add('popup-error')
  }
})

document.getElementById('input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    document.getElementById('send').click()
  }
})
