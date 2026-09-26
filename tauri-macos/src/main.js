const { invoke } = window.__TAURI__.tauri;

const messagesEl = document.getElementById('messages');
const form = document.getElementById('chat-form');
const input = document.getElementById('message-input');
const statusEl = document.getElementById('connection-status');

let conversationId = null;

function appendMessage(role, content) {
  const el = document.createElement('div');
  el.className = `message ${role}`;
  el.textContent = content;
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setStatus(text, tone = 'default') {
  statusEl.textContent = text;
  statusEl.style.color = tone === 'error' ? '#f87171' : '#22d3ee';
  statusEl.style.borderColor = tone === 'error' ? 'rgba(248,113,113,0.35)' : 'rgba(6,182,212,0.35)';
  statusEl.style.background = tone === 'error' ? 'rgba(248,113,113,0.12)' : 'rgba(6,182,212,0.12)';
}

async function sendMessage(message) {
  if (!conversationId) {
    conversationId = `tauri-${Date.now()}`;
  }

  appendMessage('user', message);
  const assistantEl = document.createElement('div');
  assistantEl.className = 'message assistant';
  assistantEl.textContent = '...';
  messagesEl.appendChild(assistantEl);

  try {
    const result = await invoke('send_message', {
      conversation_id: conversationId,
      message,
      model: 'gpt-4',
    });
    const content = result?.ai_message?.content || result?.content || JSON.stringify(result);
    assistantEl.textContent = content;
    if (result?.conversation_id) {
      conversationId = result.conversation_id;
    }
  } catch (e) {
    assistantEl.textContent = `Error: ${e?.message || e}`;
    setStatus('Error', 'error');
  } finally {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  await sendMessage(text);
});

appendMessage('system', 'Welcome to Astrovox AI Desktop');
