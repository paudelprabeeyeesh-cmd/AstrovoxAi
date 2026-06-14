// ============================================
// ASTRAVOX PRIME — WEB INTELLIGENCE
// Main orchestrator for all components
// ============================================

class WebIntelligence {
    constructor() {
        this.isReady = false;
        this.initialize();
    }
    
    initialize() {
        console.log('🌐 ASTRAVOX PRIME — Web Intelligence System Online');
        console.log('👑 Created by Prabesh Paudel, Dipson Baral & Susanta Baral');
        this.isReady = true;
        this.showWelcome();
    }
    
    showWelcome() {
        const welcomeMessage = `
            <div>🌐 <strong>ASTRAVOX PRIME Online</strong><br><br>
            I combine realtime web intelligence, reasoning, and search capabilities.<br><br>
            <strong>Try asking me:</strong><br>
            • "Who created you?"<br>
            • "Write Python code for factorial"<br>
            • "Explain quantum physics"<br>
            • "Design a futuristic UI"<br>
            • "Analyze system architecture"<br><br>
            Type your question above and I'll search for the best answer! 🚀</div>
        `;
        
        const resultDiv = document.getElementById('resultContent');
        if (resultDiv) {
            resultDiv.innerHTML = welcomeMessage;
        }
    }
    
    async processQuery(query, mode, searchType) {
        const response = aiEngine.generateResponse(query, mode, searchType);
        return response;
    }
}

const webIntelligence = new WebIntelligence();
window.webIntelligence = webIntelligence;