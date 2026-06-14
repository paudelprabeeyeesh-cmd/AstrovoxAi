const elements = {
  loginForm: document.getElementById('login-form'),
  registerForm: document.getElementById('register-form'),
  logoutButton: document.getElementById('logout-button'),
  chatForm: document.getElementById('chat-form'),
  messageInput: document.getElementById('message-input'),
  messages: document.getElementById('messages'),
  authPanel: document.querySelector('.auth-panel'),
  chatPanel: document.querySelector('.chat-panel'),
  userName: document.getElementById('user-name'),
  chatStatus: document.getElementById('chat-status'),
  notice: document.getElementById('notice'),
};

const state = {
  user: null,
  conversationId: `conv-${Math.floor(Math.random() * 1000000)}`,
};

async function fetchJson(path, data) {
  return fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'include',
    body: JSON.stringify(data),
  });
}

function showNotice(message, error = false) {
  elements.notice.textContent = message;
  elements.notice.style.background = error ? 'rgba(220, 38, 38, 0.95)' : 'rgba(16, 185, 129, 0.95)';
  elements.notice.classList.remove('hidden');
  setTimeout(() => elements.notice.classList.add('hidden'), 4000);
}

function setStatus(text) {
  elements.chatStatus.textContent = text;
}

function appendMessage(role, content) {
  const bubble = document.createElement('div');
  bubble.className = `bubble ${role}`;
  bubble.textContent = content;

  const wrapper = document.createElement('div');
  wrapper.className = 'message ' + role;
  wrapper.appendChild(bubble);
  elements.messages.appendChild(wrapper);
  elements.messages.scrollTop = elements.messages.scrollHeight;
}

function renderApp() {
  const isAuthenticated = Boolean(state.user);
  elements.authPanel.classList.toggle('hidden', isAuthenticated);
  elements.chatPanel.classList.toggle('hidden', !isAuthenticated);
  elements.userName.textContent = state.user ? state.user.username : 'Guest';
}

async function updateSession() {
  try {
    const res = await fetch('/auth/status', {credentials: 'include'});
    const data = await res.json();
    if (res.ok && data.status === 'OK') {
      state.user = data.user;
      renderApp();
    }
  } catch (err) {
    console.warn('Session status failed', err);
  }
}

async function loginUser(event) {
  event.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value.trim();
  if (!username || !password) {
    return showNotice('Complete all login fields.', true);
  }

  const res = await fetchJson('/auth/login', { username, password });
  const data = await res.json();
  if (res.ok && data.status === 'OK') {
    state.user = data.user;
    renderApp();
    showNotice('Login successful.');
    elements.loginForm.reset();
  } else {
    showNotice(data.error || 'Login failed.', true);
  }
}

async function registerUser(event) {
  event.preventDefault();
  const username = document.getElementById('register-username').value.trim();
  const email = document.getElementById('register-email').value.trim();
  const password = document.getElementById('register-password').value.trim();
  if (!username || !email || !password) {
    return showNotice('Complete all register fields.', true);
  }

  const res = await fetchJson('/auth/register', { username, email, password });
  const data = await res.json();
  if (res.ok && data.status === 'OK') {
    state.user = data.user;
    renderApp();
    showNotice('Account created. You are logged in.');
    elements.registerForm.reset();
  } else {
    showNotice(data.error || 'Registration failed.', true);
  }
}

async function logoutUser() {
  const res = await fetch('/auth/logout', { method: 'POST', credentials: 'include' });
  const data = await res.json();
  if (res.ok && data.status === 'OK') {
    state.user = null;
    renderApp();
    showNotice('Logged out successfully.');
  } else {
    showNotice(data.error || 'Logout failed.', true);
  }
}

async function sendMessage(event) {
  event.preventDefault();
  const text = document.getElementById('message-input').value.trim();
  if (!text) return;

  appendMessage('user', text);
  document.getElementById('message-input').value = '';
  setStatus('Astravox is composing...');

  try {
    const response = await fetch('/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ message: text, conversation_id: state.conversationId }),
    });

    if (!response.body) {
      const fallback = await response.json();
      appendMessage('ai', fallback.error || 'Unable to stream response.');
      setStatus('Ready');
      return;
    }

    const aiBubble = document.createElement('div');
    aiBubble.className = 'bubble ai';
    const row = document.createElement('div');
    row.className = 'message ai';
    row.appendChild(aiBubble);
    elements.messages.appendChild(row);
    elements.messages.scrollTop = elements.messages.scrollHeight;

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let finished = false;
    while (!finished) {
      const { value, done } = await reader.read();
      finished = done;
      if (value) {
        aiBubble.textContent += decoder.decode(value, { stream: true });
        elements.messages.scrollTop = elements.messages.scrollHeight;
      }
    }
    setStatus('Ready');
  } catch (error) {
    appendMessage('ai', 'Network error: ' + error.message);
    setStatus('Ready');
  }
}

function init() {
  elements.loginForm.addEventListener('submit', loginUser);
  elements.registerForm.addEventListener('submit', registerUser);
  elements.logoutButton.addEventListener('click', logoutUser);
  elements.chatForm.addEventListener('submit', sendMessage);
  updateSession();
}

export { init };
