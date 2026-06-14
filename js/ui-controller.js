function updateTime() {
    const timeElement = document.getElementById('liveTime');
    if (timeElement) {
        timeElement.textContent = new Date().toLocaleTimeString();
    }
}

function initUI() {
    updateTime();
    setInterval(updateTime, 1000);
    
    // Suggestion clicks
    document.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.dataset.query;
            if (query) {
                document.getElementById('searchInput').value = query;
                executeSearch();
            }
        });
    });
    
    // Mode chips
    document.querySelectorAll('.mode-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const mode = chip.dataset.mode;
            setMode(mode);
        });
    });
    
    // Nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const mode = item.dataset.mode;
            setMode(mode);
        });
    });
    
    // Search type buttons
    document.querySelectorAll('.search-type-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.dataset.type;
            setSearchType(type);
        });
    });
}

window.initUI = initUI;