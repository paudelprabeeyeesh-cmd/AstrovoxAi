let progress = 0;
const loaderBar = document.getElementById('loaderBar');
const percentSpan = document.getElementById('loaderPercent');
const loaderScreen = document.getElementById('loadingScreen');
if(loaderBar && percentSpan){
    const interval = setInterval(() => {
        progress += Math.random() * 12 + 8;
        if(progress >= 100){
            progress = 100;
            clearInterval(interval);
            setTimeout(() => {
                if(loaderScreen){
                    loaderScreen.style.opacity = '0';
                    setTimeout(() => loaderScreen.remove(), 500);
                }
            }, 400);
        }
        loaderBar.style.width = progress + '%';
        percentSpan.innerText = Math.floor(progress) + '%';
    }, 100);
}
function updateTime(){
    const now = new Date();
    const timeEl = document.getElementById('liveTime');
    const dateEl = document.getElementById('liveDate');
    if(timeEl) timeEl.innerText = now.toLocaleTimeString();
    if(dateEl) dateEl.innerText = now.toLocaleDateString('en-US', { weekday:'long', year:'numeric', month:'long', day:'numeric' });
}
setInterval(updateTime, 1000);
updateTime();
function showToast(message){
    const container = document.getElementById('toastContainer');
    if(!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerText = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
function showCreatorInfo(creator){
    let msg = '';
    if(creator === 'prabesh') msg = "🎯 Prabesh Paudel — Founder & Lead Architect\n\nHe designed the core AI architecture and cognitive engine. 🚀";
    else if(creator === 'dipson') msg = "⚙️ Dipson Baral — Backend & AI Systems Engineer\n\nHe built the database and server systems! 💾";
    else if(creator === 'susanta') msg = "🎨 Susanta AI — Frontend & Components Engineer\n\nHe created this beautiful interface! ✨";
    alert(msg);
}
document.querySelectorAll('.creator-card').forEach(card => card.addEventListener('click', () => showCreatorInfo(card.dataset.creator)));
document.getElementById('aiOrb')?.addEventListener('click', () => showToast("🧠 Cognitive engine ready. Ask me anything."));