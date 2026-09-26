/* Workspace frontend controller — tabs, chat, prompts, agents, documents, comments, history */

const API_BASE = '/api';
let currentWorkspaceId = localStorage.getItem('workspace_id') || 'ws-default';
let currentChannelId = localStorage.getItem('channel_id') || '';

function $(id) { return document.getElementById(id); }

function getToken() {
  return localStorage.getItem('auth_token') || '';
}

function authHeaders() {
  return {
    'Authorization': `Bearer ${getToken()}`,
    'Content-Type': 'application/json',
  };
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function timeAgo(ts) {
  const s = Math.floor((Date.now() / 1000) - ts);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

// ============================================================================
// Tabs
// ============================================================================

function initTabs() {
  document.querySelectorAll('.workspace-nav .tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.workspace-nav .tab').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = $(`tab-${btn.dataset.tab}`);
      if (panel) panel.classList.add('active');
    });
  });
}

// ============================================================================
// Overview
// ============================================================================

async function loadOverview() {
  try {
    const data = await api(`/workspaces/${currentWorkspaceId}/dashboard`);
    const overview = data.overview || {};
    $('stat-projects').textContent = overview.projects_active ?? 0;
    $('stat-tasks').textContent = overview.tasks_open ?? 0;
    $('stat-notes').textContent = overview.notes_total ?? 0;
    $('stat-members').textContent = overview.members_total ?? 0;

    const events = await api(`/workspaces/${currentWorkspaceId}/activity?limit=20`);
    const list = $('activity-list');
    list.innerHTML = '';
    (events.events || []).forEach(ev => {
      const li = document.createElement('li');
      li.textContent = `${ev.action} ${ev.type}: ${ev.title} — ${timeAgo(ev.timestamp)}`;
      list.appendChild(li);
    });
  } catch (e) {
    console.error('Failed to load overview', e);
  }
}

// ============================================================================
// Team Chat
// ============================================================================

async function loadChannels() {
  try {
    const data = await api(`/team-chat/channels?workspace_id=${encodeURIComponent(currentWorkspaceId)}`);
    const list = $('channel-list');
    list.innerHTML = '';
    (data.channels || []).forEach(ch => {
      const li = document.createElement('li');
      li.textContent = `# ${ch.name}`;
      li.dataset.channelId = ch.id;
      li.addEventListener('click', () => selectChannel(ch.id, ch.name));
      list.appendChild(li);
    });
  } catch (e) {
    console.error('Failed to load channels', e);
  }
}

async function selectChannel(channelId, name) {
  currentChannelId = channelId;
  localStorage.setItem('channel_id', channelId);
  document.querySelectorAll('#channel-list li').forEach(li => li.classList.toggle('active', li.dataset.channelId === channelId));
  $('chat-header').textContent = `# ${name || channelId}`;
  $('chat-input').disabled = false;
  $('chat-send').disabled = false;
  await loadMessages();
}

async function loadMessages() {
  if (!currentChannelId) return;
  try {
    const data = await api(`/team-chat/channels/${currentChannelId}/messages?limit=50`);
    const container = $('chat-messages');
    container.innerHTML = '';
    (data.messages || []).forEach(m => {
      const div = document.createElement('div');
      div.className = `chat-message ${m.user_id === getCurrentUserId() ? 'self' : ''}`;
      div.innerHTML = `<div class="meta">${escapeHtml(m.user_id)} · ${timeAgo(m.created_at)}</div><div>${escapeHtml(m.content)}</div>`;
      container.appendChild(div);
    });
    container.scrollTop = container.scrollHeight;
  } catch (e) {
    console.error('Failed to load messages', e);
  }
}

async function sendChatMessage() {
  const input = $('chat-input');
  const content = input.value.trim();
  if (!content || !currentChannelId) return;
  try {
    await api('/team-chat/messages', {
      method: 'POST',
      body: JSON.stringify({ channel_id: currentChannelId, content }),
    });
    input.value = '';
    await loadMessages();
  } catch (e) {
    console.error('Failed to send message', e);
  }
}

function getCurrentUserId() {
  try {
    const payload = JSON.parse(atob(getToken().split('.')[1] || ''));
    return payload.sub || payload.user_id || '';
  } catch {
    return '';
  }
}

async function createChannel() {
  const name = prompt('Channel name:');
  if (!name) return;
  try {
    await api(`/team-chat/channels?workspace_id=${encodeURIComponent(currentWorkspaceId)}`, {
      method: 'POST',
      body: JSON.stringify({ name, channel_type: 'team', member_ids: [] }),
    });
    await loadChannels();
  } catch (e) {
    alert(e.message);
  }
}

// ============================================================================
// Shared Prompts
// ============================================================================

async function loadPrompts() {
  try {
    const data = await api(`/collaboration/prompts?workspace_id=${encodeURIComponent(currentWorkspaceId)}`);
    const container = $('prompts-list');
    container.innerHTML = '';
    (data.prompts || []).forEach(p => {
      const div = document.createElement('div');
      div.className = 'list-card';
      div.innerHTML = `<h4>${escapeHtml(p.name)}</h4><p>${escapeHtml(p.description || '')}</p><div class="meta">v${escapeHtml(p.version)} · owner: ${escapeHtml(p.owner_id)}</div>`;
      container.appendChild(div);
    });
  } catch (e) {
    console.error('Failed to load prompts', e);
  }
}

async function createPrompt() {
  const name = prompt('Prompt name:');
  if (!name) return;
  const content = prompt('Prompt content:') || '';
  try {
    await api(`/collaboration/prompts?workspace_id=${encodeURIComponent(currentWorkspaceId)}`, {
      method: 'POST',
      body: JSON.stringify({ name, content, description: '' }),
    });
    await loadPrompts();
  } catch (e) {
    alert(e.message);
  }
}

// ============================================================================
// Shared Agents
// ============================================================================

async function loadAgents() {
  try {
    const data = await api(`/collaboration/agents?workspace_id=${encodeURIComponent(currentWorkspaceId)}`);
    const container = $('agents-list');
    container.innerHTML = '';
    (data.agents || []).forEach(a => {
      const div = document.createElement('div');
      div.className = 'list-card';
      div.innerHTML = `<h4>${escapeHtml(a.name)}</h4><p>${escapeHtml(a.role)} · ${escapeHtml(a.model)}</p><div class="meta">owner: ${escapeHtml(a.owner_id)} · shared: ${a.is_shared}</div>`;
      container.appendChild(div);
    });
  } catch (e) {
    console.error('Failed to load agents', e);
  }
}

async function createAgent() {
  const name = prompt('Agent name:');
  if (!name) return;
  const role = prompt('Agent role:') || 'assistant';
  const systemPrompt = prompt('System prompt:') || '';
  try {
    await api(`/collaboration/agents?workspace_id=${encodeURIComponent(currentWorkspaceId)}`, {
      method: 'POST',
      body: JSON.stringify({ name, role, system_prompt: systemPrompt, model: 'gpt-4' }),
    });
    await loadAgents();
  } catch (e) {
    alert(e.message);
  }
}

// ============================================================================
// Shared Documents
// ============================================================================

async function loadDocuments() {
  try {
    const data = await api(`/collaboration/documents?workspace_id=${encodeURIComponent(currentWorkspaceId)}`);
    const container = $('documents-list');
    container.innerHTML = '';
    (data.documents || []).forEach(d => {
      const div = document.createElement('div');
      div.className = 'list-card';
      div.innerHTML = `<h4>${escapeHtml(d.title)}</h4><p>format: ${escapeHtml(d.format)}</p><div class="meta">owner: ${escapeHtml(d.owner_id)} · updated: ${timeAgo(d.updated_at)}</div>`;
      container.appendChild(div);
    });
  } catch (e) {
    console.error('Failed to load documents', e);
  }
}

async function createDocument() {
  const title = prompt('Document title:');
  if (!title) return;
  try {
    await api(`/collaboration/documents?workspace_id=${encodeURIComponent(currentWorkspaceId)}`, {
      method: 'POST',
      body: JSON.stringify({ title, content: '', format: 'markdown' }),
    });
    await loadDocuments();
  } catch (e) {
    alert(e.message);
  }
}

// ============================================================================
// Comments
// ============================================================================

async function loadComments() {
  const resourceType = $('comment-resource-type').value;
  const resourceId = $('comment-resource-id').value.trim();
  if (!resourceId) return alert('Resource ID required');
  try {
    const data = await api(`/collaboration/comments?resource_type=${encodeURIComponent(resourceType)}&resource_id=${encodeURIComponent(resourceId)}`);
    const container = $('comments-list');
    container.innerHTML = '';
    (data.comments || []).forEach(c => {
      const div = document.createElement('div');
      div.className = 'comment-item';
      div.innerHTML = `<div class="meta">${escapeHtml(c.author_id)} · ${timeAgo(c.created_at)} · resolved: ${c.is_resolved}</div><div>${escapeHtml(c.content)}</div>`;
      container.appendChild(div);
    });
  } catch (e) {
    console.error('Failed to load comments', e);
  }
}

async function postComment() {
  const resourceType = $('comment-resource-type').value;
  const resourceId = $('comment-resource-id').value.trim();
  const content = $('comment-input').value.trim();
  if (!resourceId || !content) return;
  try {
    await api(`/collaboration/comments?workspace_id=${encodeURIComponent(currentWorkspaceId)}`, {
      method: 'POST',
      body: JSON.stringify({ resource_type: resourceType, resource_id: resourceId, content }),
    });
    $('comment-input').value = '';
    await loadComments();
  } catch (e) {
    alert(e.message);
  }
}

// ============================================================================
// Version History
// ============================================================================

async function loadVersionHistory() {
  const resourceType = $('history-resource-type').value;
  const resourceId = $('history-resource-id').value.trim();
  if (!resourceId) return alert('Resource ID required');
  try {
    const data = await api(`/collaboration/versions?resource_type=${encodeURIComponent(resourceType)}&resource_id=${encodeURIComponent(resourceId)}&limit=50`);
    const list = $('history-list');
    list.innerHTML = '';
    (data.versions || []).forEach(v => {
      const li = document.createElement('li');
      li.innerHTML = `<div>${escapeHtml(v.description || 'Version ' + v.id.slice(0, 8))}</div><div class="meta">by ${escapeHtml(v.author_id)} · ${timeAgo(v.created_at)}</div>`;
      list.appendChild(li);
    });
  } catch (e) {
    console.error('Failed to load history', e);
  }
}

// ============================================================================
// Live Collaboration WebSocket
// ============================================================================

let collaborationWs = null;

function connectCollaborationWs(resourceType, resourceId) {
  const token = getToken();
  if (!token) return;
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${protocol}//${location.host}/realtime/collaboration/${encodeURIComponent(resourceType)}/${encodeURIComponent(resourceId)}?token=${encodeURIComponent(token)}`;
  collaborationWs = new WebSocket(url);
  collaborationWs.onopen = () => console.log('Collaboration WS connected');
  collaborationWs.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'cursor_move') {
        updateRemoteCursor(msg.user_id, msg.x, msg.y, msg.color);
      } else if (msg.type === 'selection_change') {
        updateRemoteSelection(msg.user_id, msg.start, msg.end);
      } else if (msg.type === 'presence') {
        updatePresence(msg);
      }
    } catch {}
  };
  collaborationWs.onclose = () => console.log('Collaboration WS closed');
  collaborationWs.onerror = (err) => console.error('Collaboration WS error', err);
}

function sendCollaborationEvent(payload) {
  if (collaborationWs && collaborationWs.readyState === WebSocket.OPEN) {
    collaborationWs.send(JSON.stringify(payload));
  }
}

function updateRemoteCursor(userId, x, y, color) {
  let el = document.getElementById(`cursor-${userId}`);
  if (!el) {
    el = document.createElement('div');
    el.id = `cursor-${userId}`;
    el.className = 'remote-cursor';
    el.style.position = 'absolute';
    el.style.width = '8px';
    el.style.height = '8px';
    el.style.borderRadius = '50%';
    el.style.pointerEvents = 'none';
    el.style.zIndex = 9999;
    document.body.appendChild(el);
  }
  el.style.left = `${x}px`;
  el.style.top = `${y}px`;
  el.style.backgroundColor = color || '#fff';
}

function updateRemoteSelection(userId, start, end) {
  // Placeholder for remote selection highlighting
}

function updatePresence(msg) {
  // Placeholder for presence UI updates
}

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  initTabs();

  $('user-info').textContent = `Workspace: ${currentWorkspaceId}`;

  loadOverview();
  loadChannels();
  loadPrompts();
  loadAgents();
  loadDocuments();

  $('chat-send').addEventListener('click', sendChatMessage);
  $('chat-input').addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter') sendChatMessage();
  });
  $('create-channel-btn').addEventListener('click', createChannel);

  $('create-prompt-btn').addEventListener('click', createPrompt);
  $('create-agent-btn').addEventListener('click', createAgent);
  $('create-document-btn').addEventListener('click', createDocument);

  $('load-comments-btn').addEventListener('click', loadComments);
  $('comment-submit').addEventListener('click', postComment);

  $('load-history-btn').addEventListener('click', loadVersionHistory);
});
