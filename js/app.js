// ========== LOADING SCREEN PROGRESS ==========
let progress = 0;
const loaderBar = document.getElementById('loaderBar');
const percentSpan = document.getElementById('loaderPercent');
const loaderScreen = document.getElementById('loadingScreen');

if (loaderBar && percentSpan) {
    const interval = setInterval(() => {
        progress += Math.random() * 12 + 8;
        if (progress >= 100) {
            progress = 100;
            clearInterval(interval);
            setTimeout(() => {
                if (loaderScreen) {
                    loaderScreen.style.opacity = '0';
                    setTimeout(() => loaderScreen.remove(), 500);
                }
            }, 400);
        }
        loaderBar.style.width = progress + '%';
        percentSpan.innerText = Math.floor(progress) + '%';
    }, 100);
}

// ========== TIME UPDATE ==========
function updateTime() {
    const now = new Date();
    const timeEl = document.getElementById('liveTime');
    const dateEl = document.getElementById('liveDate');
    if (timeEl) timeEl.innerText = now.toLocaleTimeString();
    if (dateEl) dateEl.innerText = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
}
setInterval(updateTime, 1000);
updateTime();

// ========== CHAT HANDLING ==========
let messages = [];

function addMessageToUI(containerId, text, isUser, time = new Date().toLocaleTimeString()) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const div = document.createElement('div');
    div.className = `message ${isUser ? 'user' : 'bot'}`;
    div.innerHTML = `
        <div class="message-avatar">${isUser ? '👤' : '🧠'}</div>
        <div class="message-bubble">
            ${text.replace(/\n/g,'<br>').replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>')}
            <div class="message-time">${time}</div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function saveMessage(text, isUser) {
    messages.push({ text, isUser, time: new Date().toLocaleTimeString() });
    if (messages.length > 200) messages = messages.slice(-200);
    localStorage.setItem('astravox_chat', JSON.stringify(messages));
}

function loadChat() {
    const saved = localStorage.getItem('astravox_chat');
    if (saved) {
        messages = JSON.parse(saved);
        messages.forEach(m => addMessageToUI('chatMessages', m.text, m.isUser, m.time));
    }
    if (messages.length === 0) {
        const welcome = "Neural link established. I am ASTRAVOX PRIME. Ask me who created me!";
        addMessageToUI('chatMessages', welcome, false);
        saveMessage(welcome, false);
    }
}

function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text) return;
    if (text === '/clear') {
        messages = [];
        document.getElementById('chatMessages').innerHTML = '';
        addMessageToUI('chatMessages', "🧠 Chat history cleared.", false);
        localStorage.removeItem('astravox_chat');
        input.value = '';
        return;
    }
    addMessageToUI('chatMessages', text, true);
    saveMessage(text, true);
    input.value = '';
    const response = aiEngine.generateResponse(text);
    setTimeout(() => {
        addMessageToUI('chatMessages', response, false);
        saveMessage(response, false);
    }, 400);
}

// ========== WIDGET TOGGLE ==========
function toggleWidget() {
    const widget = document.getElementById('chatWidget');
    const toggleBtn = document.getElementById('widgetToggleBtn');
    widget.classList.toggle('minimized');
    toggleBtn.innerText = widget.classList.contains('minimized') ? '+' : '−';
}

// ========== PAGE NAVIGATION ==========
function switchPage(page) {
    document.querySelectorAll('.page-view').forEach(v => v.classList.remove('active'));
    document.getElementById(`${page}View`).classList.add('active');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-page="${page}"]`).classList.add('active');
}

// ========== CREATOR INFO ==========
function showCreatorInfo(creator) {
    let msg = '';
    if (creator === 'prabesh') msg = "🎯 Prabesh Paudel — Founder & Lead Architect\n\nHe designed the core AI architecture and cognitive engine. 🚀";
    else if (creator === 'dipson') msg = "⚙️ Dipson Baral — Backend & AI Systems Engineer\n\nHe built the database and server systems! 💾";
    else if (creator === 'susanta') msg = "🎨 Susanta AI — Frontend & Components Engineer\n\nHe created this beautiful interface! ✨";
    alert(msg);
}

// ========== TOAST ==========
function showToast(message) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerText = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ========== EVENT LISTENERS ==========
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('chatSendBtn')?.addEventListener('click', sendChatMessage);
    document.getElementById('chatInput')?.addEventListener('keypress', e => { if (e.key === 'Enter') sendChatMessage(); });
    document.getElementById('chatSendFull')?.addEventListener('click', () => {
        const input = document.getElementById('chatInputFull');
        const text = input.value.trim();
        if (!text) return;
        addMessageToUI('chatMessagesFull', text, true);
        input.value = '';
        const response = aiEngine.generateResponse(text);
        setTimeout(() => addMessageToUI('chatMessagesFull', response, false), 300);
    });
    document.getElementById('chatInputFull')?.addEventListener('keypress', e => { if (e.key === 'Enter') document.getElementById('chatSendFull').click(); });
    document.getElementById('chatWidgetHeader')?.addEventListener('click', toggleWidget);
    document.getElementById('aiOrb')?.addEventListener('click', () => showToast("🧠 Cognitive engine ready. Ask me anything."));
    document.querySelectorAll('.creator-card').forEach(card => card.addEventListener('click', () => showCreatorInfo(card.dataset.creator)));
    document.querySelectorAll('.nav-item').forEach(item => item.addEventListener('click', () => switchPage(item.dataset.page)));
    document.querySelectorAll('.dashboard-card').forEach(card => card.addEventListener('click', () => showToast(`📊 ${card.querySelector('.card-title')?.innerText || 'Module'} activated`)));

    loadChat();
});

// ========== MOBILE SIDEBAR TOGGLE ==========
const mobileBtn = document.createElement('button');
mobileBtn.innerHTML = '☰';
mobileBtn.style.cssText = 'position:fixed; bottom:20px; left:20px; background:rgba(0,0,0,0.6); border:1px solid #00F2FE; color:#00F2FE; width:44px; height:44px; border-radius:50%; z-index:300; cursor:pointer; backdrop-filter:blur(10px); display:none;';
mobileBtn.onclick = () => document.getElementById('sidebar').classList.toggle('open');
document.body.appendChild(mobileBtn);

function checkMobile() {
    if (window.innerWidth <= 1024) mobileBtn.style.display = 'block';
    else mobileBtn.style.display = 'none';
}
window.addEventListener('resize', checkMobile);
checkMobile();

console.log('ASTRAVOX PRIME — Fully operational');