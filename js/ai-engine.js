class AstraVoxAI {
    constructor() {
        this.name = "ASTRAVOX PRIME";
        this.version = "4.0.0";
        this.creators = [
            { name: "Prabesh Paudel", role: "Founder & Lead Architect" },
            { name: "Dipson Baral", role: "Backend & AI Systems Engineer" },
            { name: "Susanta AI", role: "Frontend & Components Engineer" }
        ];
        this.memory = [];
        this.loadMemory();
    }

    loadMemory() {
        const saved = localStorage.getItem('astravox_memory');
        if (saved) this.memory = JSON.parse(saved);
    }
    saveMemory() {
        localStorage.setItem('astravox_memory', JSON.stringify(this.memory.slice(-200)));
    }

    async process(input) {
        const response = this.generateResponse(input);
        this.memory.push({ input, response, time: Date.now() });
        this.saveMemory();
        return response;
    }

    generateResponse(input) {
        const q = input.toLowerCase().trim();

        if (q.includes('who created you') || q.includes('who made you')) {
            return `🧠 **ASTRAVOX PRIME Development Team**\n\n🎯 Prabesh Paudel — Founder & Lead Architect\n⚙️ Dipson Baral — Backend & AI Systems Engineer\n🎨 Susanta AI — Frontend & Components Engineer\n\nTogether they built this sovereign AI operating system! 🚀`;
        }
        if (q.includes('prabesh')) return "🎯 **Prabesh Paudel** — Founder & Lead Architect, visionary behind ASTRAVOX PRIME.";
        if (q.includes('dipson')) return "⚙️ **Dipson Baral** — Backend & AI Systems Engineer, built memory and server architecture.";
        if (q.includes('susanta')) return "🎨 **Susanta AI** — Frontend & Components Engineer, created the glassmorphic interface.";
        if (q.match(/^(hi|hello|hey)/)) return "👋 Neural link active. I am ASTRAVOX PRIME. Ask me about my creators, coding, science, or just chat!";
        if (q.includes('joke')) return "🤣 Why did the AI go to school? To improve its intelligence!";
        if (q.includes('name')) return "I am ASTRAVOX PRIME, your cognitive engine created by Prabesh Paudel, Dipson Baral, and Susanta AI.";
        if (q.includes('time')) return `🕐 ${new Date().toLocaleTimeString()}`;
        if (q.includes('help')) return "📚 Commands: 'Who created you?', 'Prabesh', 'Dipson', 'Susanta', 'joke', 'time', 'clear chat'";
        if (q.includes('clear chat')) {
            this.memory = [];
            localStorage.removeItem('astravox_memory');
            return "🧹 Chat history cleared. Memory reset.";
        }
        return `🧠 I understand: "${input}". Type "help" for available commands. I am your cognitive engine.`;
    }
}

const aiEngine = new AstraVoxAI();
window.aiEngine = aiEngine;