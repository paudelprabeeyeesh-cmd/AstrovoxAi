function setMode(mode) {
    currentMode = mode;
    
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.mode === mode) item.classList.add('active');
    });
    
    document.querySelectorAll('.mode-chip').forEach(chip => {
        chip.classList.remove('active');
        if (chip.dataset.mode === mode) chip.classList.add('active');
    });
    
    const statusTexts = {
        web: '🌐 Web Intelligence Active',
        research: '🔬 Research Mode Active',
        coding: '💻 Coding Mode Active',
        analysis: '📊 Analysis Mode Active',
        creator: '🎨 Creator Mode Active'
    };
    
    const searchStatus = document.getElementById('searchStatus');
    if (searchStatus) searchStatus.innerHTML = statusTexts[mode] || '🌐 Web Intelligence Active';
}

window.setMode = setMode;