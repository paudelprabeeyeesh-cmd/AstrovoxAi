let messages = [];
function addMessageToUI(containerId, text, isUser, time = new Date().toLocaleTimeString()){
    const container = document.getElementById(containerId);
    if(!container) return;
    const div = document.createElement('div');
    div.className = `message ${isUser ? 'user' : 'bot'}`;
    div.innerHTML = `<div class="message-avatar">${isUser ? '👤' : '🧠'}</div><div class="message-bubble">${text.replace(/\n/g,'<br>').replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>')}<div class="message-time">${time}</div></div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}
function saveMessage(text, isUser){
    messages.push({ text, isUser, time: new Date().toLocaleTimeString() });
    if(messages.length > 200) messages = messages.slice(-200);
    localStorage.setItem('astravox_chat', JSON.stringify(messages));
}
function loadChat(){
    const saved = localStorage.getItem('astravox_chat');
    if(saved){
        messages = JSON.parse(saved);
        messages.forEach(m => addMessageToUI('chatMessages', m.text, m.isUser, m.time));
    }
    if(messages.length===0){
        const welcome = "Neural link established. I am ASTRAVOX PRIME. Ask me who created me!";
        addMessageToUI('chatMessages', welcome, false);
        saveMessage(welcome, false);
    }
}
function sendChatMessage(){
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if(!text) return;
    if(text === '/clear'){
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
    const response = window.aiCore ? window.aiCore.generateResponse(text) : "AI core not ready.";
    setTimeout(() => {
        addMessageToUI('chatMessages', response, false);
        saveMessage(response, false);
    }, 400);
}
function sendFullChatMessage(){
    const input = document.getElementById('chatInputFull');
    const text = input.value.trim();
    if(!text) return;
    addMessageToUI('chatMessagesFull', text, true);
    input.value = '';
    const response = window.aiCore ? window.aiCore.generateResponse(text) : "AI core not ready.";
    setTimeout(() => addMessageToUI('chatMessagesFull', response, false), 300);
}
function toggleWidget(){
    const widget = document.getElementById('chatWidget');
    const toggleBtn = document.getElementById('widgetToggleBtn');
    widget.classList.toggle('minimized');
    toggleBtn.innerText = widget.classList.contains('minimized') ? '+' : '−';
}
document.getElementById('chatSendBtn')?.addEventListener('click', sendChatMessage);
document.getElementById('chatInput')?.addEventListener('keypress', e => { if(e.key === 'Enter') sendChatMessage(); });
document.getElementById('chatSendFull')?.addEventListener('click', sendFullChatMessage);
document.getElementById('chatInputFull')?.addEventListener('keypress', e => { if(e.key === 'Enter') document.getElementById('chatSendFull').click(); });
document.getElementById('chatWidgetHeader')?.addEventListener('click', toggleWidget);
loadChat();