(function () {
  'use strict';

  if (!window.AstrovoxReality) {
    window.AstrovoxReality = {};
  }

  const Reality = window.AstrovoxReality;

  const GRAVITY_STATES = ['float', 'heavy', 'zero'];
  const TIME_STATES = ['normal', 'dilated', 'frozen', 'fast'];
  const SENSITIVE_SELECTORS = [
    '.message', '.message-bubble', '.conversation-item',
    '.stat-card', '.activity-item', '.activity-desc',
    '#message-input', '#email', '#password', '#confirmPassword'
  ];

  let cursorFollower = null;
  let cursorRaf = null;
  let lastCursor = { x: 0, y: 0 };
  let targetCursor = { x: 0, y: 0 };
  let glitchTimer = null;
  let multiverseState = {};
  let clonedElements = [];
  let currentGravity = 'normal';
  let currentTimeMode = 'normal';
  let invisibleMode = false;
  let intangibleMode = false;
  let transcendentMode = false;
  let debugPanelEl = null;

  function init() {
    if (typeof window === 'undefined') return;
    _initCursorFollower();
    _bindKeyboardShortcuts();
    _bindAppHooks();
    _restoreState();
  }

  function _restoreState() {
    try {
      const state = JSON.parse(localStorage.getItem('astrovox_reality_state') || '{}');
      if (state.gravity) setGravity(state.gravity, true);
      if (state.timeMode) setTimeMode(state.timeMode, true);
      if (state.invisible) toggleInvisibility(true);
      if (state.intangible) toggleIntangibility(true);
      if (state.transcendent) toggleTranscendent(true);
      if (state.multiverse) Object.assign(multiverseState, state.multiverse);
    } catch {}
  }

  function _persistState() {
    try {
      localStorage.setItem('astrovox_reality_state', JSON.stringify({
        gravity: currentGravity,
        timeMode: currentTimeMode,
        invisible: invisibleMode,
        intangible: intangibleMode,
        transcendent: transcendentMode,
        multiverse: multiverseState,
      }));
    } catch {}
  }

  function _bindAppHooks() {
    document.addEventListener('DOMContentLoaded', () => {
      _applyGravityToExistingPanels();
      _syncMultiverse();
    });

    const origPush = History.prototype.pushState;
    if (origPush) {
      History.prototype.pushState = function () {
        origPush.apply(this, arguments);
        _onRouteChange();
      };
    }

    window.addEventListener('hashchange', () => {
      _onRouteChange();
    });
  }

  function _onRouteChange() {
    if (typeof window.app !== 'undefined' && window.app._checkAuthAndRoute) {
      requestAnimationFrame(() => _applyGravityToExistingPanels());
    }
  }

  function _applyGravityToExistingPanels() {
    if (currentGravity === 'normal') return;
    document.querySelectorAll('.chat-sidebar, .chat-main, .dashboard-card, .stat-card').forEach(el => {
      el.classList.add('rbp-gravity-panel');
      el.setAttribute('data-gravity', currentGravity);
    });
  }

  function _bindKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'g') {
        e.preventDefault();
        cycleGravity();
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 't') {
        e.preventDefault();
        cycleTimeMode();
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'i') {
        e.preventDefault();
        toggleInvisibility();
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        toggleIntangibility();
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'r') {
        e.preventDefault();
        triggerRealityGlitch();
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'm') {
        e.preventDefault();
        toggleTranscendent();
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'd') {
        e.preventDefault();
        toggleDebugPanel();
      }
    });
  }

  /* ============ 1. Gravity-defying panels ============ */
  function setGravity(state, silent) {
    if (!GRAVITY_STATES.includes(state)) return;
    currentGravity = state;
    document.querySelectorAll('.rbp-gravity-panel').forEach(el => {
      el.setAttribute('data-gravity', state);
    });
    if (!silent) _persistState();
  }

  function cycleGravity() {
    const idx = (GRAVITY_STATES.indexOf(currentGravity) + 1) % GRAVITY_STATES.length;
    setGravity(GRAVITY_STATES[idx]);
    showToast('Gravity mode: ' + GRAVITY_STATES[idx]);
  }

  function enableGravityPanels(selector) {
    document.querySelectorAll(selector || '.rbp-gravity-panel').forEach(el => {
      el.classList.add('rbp-gravity-panel');
      el.setAttribute('data-gravity', currentGravity);
    });
  }

  /* ============ 2. Time-dilated animations ============ */
  function setTimeMode(mode, silent) {
    if (!TIME_STATES.includes(mode)) return;
    currentTimeMode = mode;
    document.body.classList.remove('rbp-time-dilated', 'rbp-time-frozen', 'rbp-time-fast');
    if (mode !== 'normal') {
      document.body.classList.add('rbp-time-' + mode);
    }
    if (!silent) _persistState();
  }

  function cycleTimeMode() {
    const idx = (TIME_STATES.indexOf(currentTimeMode) + 1) % TIME_STATES.length;
    setTimeMode(TIME_STATES[idx]);
    showToast('Time mode: ' + TIME_STATES[idx]);
  }

  function getTimeScale() {
    if (currentTimeMode === 'dilated') return 3;
    if (currentTimeMode === 'fast') return 0.3;
    if (currentTimeMode === 'frozen') return 0;
    return 1;
  }

  /* ============ 3. Wormhole navigation ============ */
  function teleportToConversation(conversationEl) {
    if (!conversationEl) return;
    conversationEl.classList.add('rbp-wormhole-enter');
    setTimeout(() => {
      conversationEl.classList.remove('rbp-wormhole-enter');
      conversationEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 600);
  }

  function wormholeNavigateToConversation(conversationId) {
    const convEl = document.querySelector(`.conversation-item[data-id="${CSS.escape(conversationId)}"]`);
    if (convEl) teleportToConversation(convEl);
  }

  function wormholeNavigateToElement(selector) {
    const el = document.querySelector(selector);
    if (el) teleportToConversation(el);
  }

  /* ============ 4. Teleportation workspace switching ============ */
  function teleportToWorkspace(workspace) {
    let overlay = document.querySelector('.rbp-teleport-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'rbp-teleport-overlay';
      document.body.appendChild(overlay);
    }
    overlay.classList.remove('active');
    void overlay.offsetWidth;
    overlay.classList.add('active');
    setTimeout(() => {
      overlay.classList.remove('active');
      if (workspace === 'chat') {
        window.location.href = '/chat.html';
      } else if (workspace === 'dashboard') {
        window.location.href = '/dashboard.html';
      }
    }, 350);
  }

  /* ============ 5. Cloning / duplication ============ */
  function cloneElement(selector, offsetX, offsetY) {
    const source = document.querySelector(selector);
    if (!source) return null;
    const rect = source.getBoundingClientRect();
    const clone = source.cloneNode(true);
    clone.classList.add('rbp-clone');
    clone.style.left = (rect.left + (offsetX || 20)) + 'px';
    clone.style.top = (rect.top + (offsetY || 20)) + 'px';
    clone.style.width = rect.width + 'px';
    document.body.appendChild(clone);
    clonedElements.push(clone);
    return clone;
  }

  function removeClones() {
    clonedElements.forEach(c => c.remove());
    clonedElements = [];
  }

  /* ============ 6. Invisibility mode ============ */
  function toggleInvisibility(force) {
    invisibleMode = typeof force === 'boolean' ? force : !invisibleMode;
    SENSITIVE_SELECTORS.forEach(sel => {
      document.querySelectorAll(sel).forEach(el => {
        el.classList.toggle('rbp-invisible', invisibleMode);
      });
    });
    _persistState();
  }

  function isInvisibilityActive() {
    return invisibleMode;
  }

  /* ============ 7. Intangibility mode ============ */
  function toggleIntangibility(force) {
    intangibleMode = typeof force === 'boolean' ? force : !intangibleMode;
    const targetSelectors = ['.chat-sidebar', '.chat-main', '.dashboard-card', '.stat-card', '.navbar'];
    targetSelectors.forEach(sel => {
      document.querySelectorAll(sel).forEach(el => {
        el.classList.toggle('rbp-intangible', intangibleMode);
      });
    });
    _persistState();
  }

  function isIntangibilityActive() {
    return intangibleMode;
  }

  /* ============ 8. Reality-warping search ============ */
  function warpSearchResults(selector) {
    const results = document.querySelectorAll(selector || '.command-palette-item, .conversation-item, .activity-item');
    results.forEach((el, i) => {
      setTimeout(() => {
        el.classList.add('rbp-warp-result');
        setTimeout(() => el.classList.remove('rbp-warp-result'), 900);
      }, i * 60);
    });
  }

  function warpElement(el) {
    if (!el) return;
    el.classList.add('rbp-warp-result');
    setTimeout(() => el.classList.remove('rbp-warp-result'), 900);
  }

  /* ============ 9. Universe-in-a-box sandboxed environments ============ */
  function createSandbox(title, contentHtml) {
    const sandbox = document.createElement('div');
    sandbox.className = 'rbp-sandbox';
    sandbox.innerHTML = `
      <div style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); display:flex; align-items:center; justify-content:space-between;">
        <span style="font-weight:600; font-size:0.875rem;">${escapeHtml(title)}</span>
        <div style="display:flex; gap:0.5rem;">
          <button class="btn btn-sm btn-secondary rbp-sandbox-close">Close</button>
        </div>
      </div>
      <div style="padding: 1rem; overflow: auto; max-height: 60vh; background: rgba(0,0,0,0.2);">
        ${contentHtml}
      </div>
    `;
    sandbox.querySelector('.rbp-sandbox-close').addEventListener('click', () => sandbox.remove());
    document.body.appendChild(sandbox);
    return sandbox;
  }

  function createIsolatedSandbox(title, srcUrl) {
    const container = document.createElement('div');
    container.className = 'rbp-sandbox';
    container.style.padding = '0';
    const iframe = document.createElement('iframe');
    iframe.src = srcUrl;
    iframe.style.cssText = 'width:100%; height:60vh; border:none; background:#fff;';
    iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin');
    container.appendChild(iframe);
    document.body.appendChild(container);
    return container;
  }

  /* ============ 10. Meta-reality debugging tools ============ */
  function toggleDebugPanel() {
    if (debugPanelEl) {
      debugPanelEl.remove();
      debugPanelEl = null;
      return;
    }
    debugPanelEl = document.createElement('div');
    debugPanelEl.className = 'rbp-debug-panel';
    debugPanelEl.innerHTML = `
      <div class="rbp-debug-panel-header">
        <span class="rbp-debug-panel-title">Meta-Reality Debugger</span>
        <button class="modal-close rbp-debug-close">&times;</button>
      </div>
      <div class="rbp-debug-panel-body" id="rbp-debug-body"></div>
    `;
    document.body.appendChild(debugPanelEl);
    debugPanelEl.querySelector('.rbp-debug-close').addEventListener('click', () => toggleDebugPanel());
    _renderDebugPanel();
  }

  function _renderDebugPanel() {
    const body = document.getElementById('rbp-debug-body');
    if (!body || !debugPanelEl) return;
    const now = new Date();
    body.innerHTML = [
      _debugRow('Gravity', currentGravity),
      _debugRow('Time Mode', currentTimeMode),
      _debugRow('Time Scale', getTimeScale().toString()),
      _debugRow('Invisible', invisibleMode ? 'ON' : 'OFF'),
      _debugRow('Intangible', intangibleMode ? 'ON' : 'OFF'),
      _debugRow('Transcendent', transcendentMode ? 'ON' : 'OFF'),
      _debugRow('Clones', clonedElements.length.toString()),
      _debugRow('Clocks', _countAnimations().toString()),
      _debugRow('UTC', now.toISOString()),
    ].join('');
  }

  function _debugRow(label, value) {
    return `<div class="rbp-debug-row"><span class="rbp-debug-label">${escapeHtml(label)}</span><span class="rbp-debug-value">${escapeHtml(value)}</span></div>`;
  }

  function _countAnimations() {
    try {
      return document.getAnimations().length;
    } catch {
      return 0;
    }
  }

  function getDebugState() {
    return {
      gravity: currentGravity,
      timeMode: currentTimeMode,
      timeScale: getTimeScale(),
      invisible: invisibleMode,
      intangible: intangibleMode,
      transcendent: transcendentMode,
      clonedElements: clonedElements.length,
      activeAnimations: _countAnimations(),
      multiverse: { ...multiverseState },
    };
  }

  function refreshDebugPanel() {
    if (debugPanelEl) _renderDebugPanel();
  }

  /* ============ 11. Physics-defying interactions ============ */
  function _initCursorFollower() {
    if (cursorFollower) return;
    cursorFollower = document.createElement('div');
    cursorFollower.className = 'rbp-physics-cursor';
    cursorFollower.setAttribute('aria-hidden', 'true');
    document.body.appendChild(cursorFollower);
    document.addEventListener('mousemove', (e) => {
      targetCursor.x = e.clientX;
      targetCursor.y = e.clientY;
    });
    _updateCursor();
  }

  function _updateCursor() {
    if (!cursorFollower) return;
    lastCursor.x += (targetCursor.x - lastCursor.x) * 0.18;
    lastCursor.y += (targetCursor.y - lastCursor.y) * 0.18;
    cursorFollower.style.transform = `translate(${lastCursor.x - 6}px, ${lastCursor.y - 6}px)`;
    cursorRaf = requestAnimationFrame(_updateCursor);
  }

  function enablePhysicsCursor(enable) {
    if (enable) {
      _initCursorFollower();
      if (cursorFollower) cursorFollower.style.display = 'block';
    } else if (cursorFollower) {
      cursorFollower.style.display = 'none';
    }
  }

  function applyPhysicsToElement(el, intensity) {
    if (!el) return;
    el.addEventListener('mousemove', (e) => {
      const rect = el.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      const scale = 1 + (intensity || 0.04);
      const rotateX = -y * 8;
      const rotateY = x * 8;
      el.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(${scale},${scale},${scale})`;
    });
    el.addEventListener('mouseleave', () => {
      el.style.transform = '';
      el.style.transition = 'transform 0.6s cubic-bezier(0.22, 1, 0.36, 1)';
    });
    el.addEventListener('mouseenter', () => {
      el.style.transition = 'none';
    });
  }

  /* ============ 12. Dimensional rifts in UI ============ */
  function enableRiftOnSelector(selector) {
    document.querySelectorAll(selector).forEach(el => {
      el.classList.add('rbp-rift');
    });
  }

  function addRiftToElement(el) {
    if (el) el.classList.add('rbp-rift');
  }

  function removeRiftFromElement(el) {
    if (el) el.classList.remove('rbp-rift');
  }

  /* ============ 13. Reality glitches and artifacts ============ */
  function triggerRealityGlitch(duration) {
    const root = document.documentElement;
    root.classList.add('rbp-glitch');
    root.setAttribute('data-text', document.title || 'AstrovoxAI');
    setTimeout(() => {
      root.classList.remove('rbp-glitch');
      root.removeAttribute('data-text');
    }, duration || 800);
  }

  function scheduleRandomGlitches(intervalMs) {
    if (glitchTimer) clearInterval(glitchTimer);
    glitchTimer = setInterval(() => {
      if (Math.random() < 0.3) triggerRealityGlitch(250);
    }, intervalMs || 12000);
  }

  function cancelRandomGlitches() {
    if (glitchTimer) {
      clearInterval(glitchTimer);
      glitchTimer = null;
    }
  }

  /* ============ 14. Multiverse state synchronization ============ */
  function _syncMultiverse() {
    const snapshot = _captureState();
    Object.assign(multiverseState, snapshot);
    _persistState();
  }

  function _captureState() {
    try {
      const token = localStorage.getItem('astrovox_access_token');
      const user = localStorage.getItem('astrovox_user');
      return {
        timestamp: Date.now(),
        token: !!token,
        user: !!user,
        gravity: currentGravity,
        timeMode: currentTimeMode,
        invisible: invisibleMode,
        transcendent: transcendentMode,
        page: window.location.pathname + window.location.hash,
      };
    } catch {
      return { timestamp: Date.now() };
    }
  }

  function getMultiverseState() {
    return { ...multiverseState };
  }

  function syncMultiverseNow() {
    _syncMultiverse();
    return getMultiverseState();
  }

  function renderMultiverseBadge(container) {
    const el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    const badge = document.createElement('span');
    badge.className = 'rbp-multiverse-badge';
    badge.innerHTML = '<span class="rbp-multiverse-dot"></span>Multiverse';
    el.appendChild(badge);
    return badge;
  }

  /* ============ 15. Transcendent UI modes ============ */
  function toggleTranscendent(force) {
    transcendentMode = typeof force === 'boolean' ? force : !transcendentMode;
    document.body.classList.toggle('rbp-transcendent-active', transcendentMode);
    document.querySelectorAll('.rbp-gravity-panel').forEach(el => {
      el.classList.toggle('rbp-transcendent', transcendentMode);
    });
    _persistState();
  }

  function isTranscendentActive() {
    return transcendentMode;
  }

  function enterTranscendence() {
    toggleTranscendent(true);
    setGravity('zero');
    setTimeMode('dilated');
    triggerRealityGlitch(600);
    showToast('Transcendence achieved');
  }

  /* ============ Utility ============ */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function showToast(message) {
    if (typeof showToast !== 'undefined' && window.showToast) {
      window.showToast(message);
    }
  }

  function destroy() {
    cancelRandomGlitches();
    if (cursorRaf) cancelAnimationFrame(cursorRaf);
    if (cursorFollower) cursorFollower.remove();
    cursorFollower = null;
    removeClones();
    if (debugPanelEl) debugPanelEl.remove();
    debugPanelEl = null;
    document.body.classList.remove('rbp-time-dilated', 'rbp-time-frozen', 'rbp-time-fast');
    document.body.classList.remove('rbp-transcendent-active');
  }

  Reality.init = init;
  Reality.setGravity = setGravity;
  Reality.cycleGravity = cycleGravity;
  Reality.enableGravityPanels = enableGravityPanels;
  Reality.setTimeMode = setTimeMode;
  Reality.cycleTimeMode = cycleTimeMode;
  Reality.getTimeScale = getTimeScale;
  Reality.teleportToConversation = teleportToConversation;
  Reality.wormholeNavigateToConversation = wormholeNavigateToConversation;
  Reality.wormholeNavigateToElement = wormholeNavigateToElement;
  Reality.teleportToWorkspace = teleportToWorkspace;
  Reality.cloneElement = cloneElement;
  Reality.removeClones = removeClones;
  Reality.toggleInvisibility = toggleInvisibility;
  Reality.isInvisibilityActive = isInvisibilityActive;
  Reality.toggleIntangibility = toggleIntangibility;
  Reality.isIntangibilityActive = isIntangibilityActive;
  Reality.warpSearchResults = warpSearchResults;
  Reality.warpElement = warpElement;
  Reality.createSandbox = createSandbox;
  Reality.createIsolatedSandbox = createIsolatedSandbox;
  Reality.toggleDebugPanel = toggleDebugPanel;
  Reality.getDebugState = getDebugState;
  Reality.refreshDebugPanel = refreshDebugPanel;
  Reality.enablePhysicsCursor = enablePhysicsCursor;
  Reality.applyPhysicsToElement = applyPhysicsToElement;
  Reality.enableRiftOnSelector = enableRiftOnSelector;
  Reality.addRiftToElement = addRiftToElement;
  Reality.removeRiftFromElement = removeRiftFromElement;
  Reality.triggerRealityGlitch = triggerRealityGlitch;
  Reality.scheduleRandomGlitches = scheduleRandomGlitches;
  Reality.cancelRandomGlitches = cancelRandomGlitches;
  Reality.getMultiverseState = getMultiverseState;
  Reality.syncMultiverseNow = syncMultiverseNow;
  Reality.renderMultiverseBadge = renderMultiverseBadge;
  Reality.toggleTranscendent = toggleTranscendent;
  Reality.isTranscendentActive = isTranscendentActive;
  Reality.enterTranscendence = enterTranscendence;
  Reality.destroy = destroy;
  Reality._GRAVITY_STATES = GRAVITY_STATES;
  Reality._TIME_STATES = TIME_STATES;
  Reality._SENSITIVE_SELECTORS = SENSITIVE_SELECTORS;
})();
