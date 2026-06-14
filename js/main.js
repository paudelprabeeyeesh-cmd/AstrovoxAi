// ============================================
// ASTRAVOX PRIME — MAIN APPLICATION
// Created by Prabesh Paudel, Dipson Baral, Susanta Baral
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🧠 ASTRAVOX PRIME — Sovereign AI Operating System');
    console.log('👑 Created by Prabesh Paudel, Dipson Baral & Susanta Baral');
    console.log('⚡ All systems operational');
    
    // Initialize UI
    initUI();
    
    // Set welcome message
    const resultDiv = document.getElementById('resultContent');
    if (resultDiv) {
        resultDiv.innerHTML = `
            <div>🌐 <strong>ASTRAVOX PRIME Online</strong><br><br>
            I combine web intelligence, reasoning, and search capabilities.<br><br>
            <strong>Try asking me:</strong><br>
            • "Who created you?"<br>
            • "Python async/await tutorial"<br>
            • "Quantum computing explained"<br>
            • "Latest AI developments"<br><br>
            Type your question above! 🚀</div>
        `;
    }
});