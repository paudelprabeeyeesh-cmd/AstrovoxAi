let currentMode = 'web';
let searchType = 'web';

function executeSearch() {
    const input = document.getElementById('searchInput');
    const query = input.value.trim();
    if (!query) return;
    
    const resultDiv = document.getElementById('resultContent');
    const resultMode = document.getElementById('resultMode');
    
    resultDiv.innerHTML = `<div class="thinking"><span>🧠 Searching web intelligence...</span><div class="thinking-dots"><span></span><span></span><span></span></div></div>`;
    
    setTimeout(() => {
        const response = aiEngine.generateResponse(query, currentMode);
        resultDiv.innerHTML = response;
        
        const modeNames = { web: '🌐 Web Mode', research: '🔬 Research Mode', coding: '💻 Coding Mode', analysis: '📊 Analysis Mode', creator: '🎨 Creator Mode' };
        resultMode.innerHTML = modeNames[currentMode] || '🌐 Web Mode';
        
        document.getElementById('searchStatus').innerHTML = '✅ Search complete';
        document.getElementById('connectionStatus').innerHTML = 'REALTIME SEARCH READY';
    }, 800);
}

function setSearchType(type) {
    searchType = type;
    document.querySelectorAll('.search-type-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.type === type) btn.classList.add('active');
    });
}

window.executeSearch = executeSearch;
window.setSearchType = setSearchType;