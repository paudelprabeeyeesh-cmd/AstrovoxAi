// ============================================
// PRABESH PAUDEL — COMMAND SYSTEM
// Command System Creator | Full-Stack Developer
// ============================================

class CommandSystem {
    constructor() {
        this.commands = new Map();
        this.initCommands();
        this.commandHistory = [];
    }
    
    initCommands() {
        // Core Commands
        this.register('/help', 'Show all commands', () => this.showHelp());
        this.register('/clear', 'Clear conversation', () => this.clearChat());
        this.register('/theme', 'Toggle dark/light mode', () => this.toggleTheme());
        this.register('/stats', 'Show system statistics', () => this.showStats());
        this.register('/export', 'Export chat history', () => this.exportChat());
        this.register('/voice', 'Toggle voice mode', () => this.toggleVoice());
        
        // Creator Commands
        this.register('/prabesh', 'About Prabesh Paudel', () => this.showPrabesh());
        this.register('/creator', 'About the creator', () => this.showCreator());
        this.register('/team', 'About the development team', () => this.showTeam());
        
        // Info Commands
        this.register('/about', 'About ASTRAVOX-AI', () => this.showAbout());
        this.register('/time', 'Current time', () => this.showTime());
        this.register('/date', 'Today\'s date', () => this.showDate());
    }
    
    register(name, description, handler) {
        this.commands.set(name, { description, handler });
    }
    
    execute(input) {
        const parts = input.trim().split(' ');
        const command = parts[0].toLowerCase();
        const args = parts.slice(1);
        
        if (this.commands.has(command)) {
            const result = this.commands.get(command).handler(args);
            this.commandHistory.push({ command, args, timestamp: Date.now() });
            return result;
        }
        
        return null;
    }
    
    showHelp() {
        let helpText = `📚 **ASTRAVOX-AI Commands — Created by Prabesh Paudel**\n\n`;
        
        helpText += `**🎯 Core Commands:**\n`;
        for (const [cmd, info] of this.commands) {
            if (cmd.startsWith('/') && !cmd.startsWith('/pra') && !cmd.startsWith('/cre') && !cmd.startsWith('/team')) {
                helpText += `• \`${cmd}\` — ${info.description}\n`;
            }
        }
        
        helpText += `\n**👤 Creator Commands:**\n`;
        helpText += `• \`/prabesh\` — About Prabesh Paudel (Founder)\n`;
        helpText += `• \`/creator\` — About the creator\n`;
        helpText += `• \`/team\` — About the development team\n`;
        
        helpText += `\n**💡 Try: "Who created you?" or "Tell me about Prabesh"**`;
        
        return this.formatResponse(helpText);
    }
    
    showPrabesh() {
        return this.formatResponse(`
            👑 **Prabesh Paudel — Founder, Lead Developer & Chief AI Architect**
            
            **Current Roles:**
            • Founder of AstraVox AI
            • Lead AI Developer
            • Full-Stack Web Developer
            • AI System Architect
            • Frontend Engineer
            • Backend Engineer
            • UI/UX Designer
            • Prompt Engineer
            • API Integration Developer
            • Database Manager
            • Voice AI Developer
            • Command System Creator
            • 3D Interface Designer
            • Real-Time Chat System Developer
            • Deployment Manager
            • Performance Optimizer
            • Security Controller
            • Product Vision Director
            
            **Vision:** "To develop a next-generation AI ecosystem capable of intelligent conversation, adaptive reasoning, immersive interaction, and advanced human-AI collaboration."
        `);
    }
    
    showCreator() {
        return this.formatResponse(`
            🧠 **About My Creator — Prabesh Paudel**
            
            Prabesh Paudel is the Founder, Lead Developer & Chief AI Architect of AstraVox AI.
            
            He built this entire cognitive operating system from scratch, handling:
            • AI Architecture & Development
            • Frontend & Backend Engineering
            • UI/UX Design
            • Voice AI Integration
            • Database Management
            • Deployment & Security
            
            His vision: "Making advanced AI accessible to everyone." 🚀
        `);
    }
    
    showTeam() {
        return this.formatResponse(`
            🎯 **ASTRAVOX-AI Development Team**
            
            **Prabesh Paudel** — Founder, Lead Developer & Chief AI Architect
            • AI Architecture | Full-Stack Development | UI/UX Design
            
            **Built by Prabesh Paudel** with passion and expertise! 🚀
        `);
    }
    
    showAbout() {
        return this.formatResponse(`
            🧠 **ASTRAVOX-AI v3.0 — Cognitive Operating System**
            
            **Created by:** Prabesh Paudel
            **Version:** 3.0.0
            **Type:** Advanced AI Cognitive Engine
            
            **Features:**
            • Real-time AI conversations
            • Voice recognition & synthesis
            • 3D WebGL graphics
            • Glassmorphism UI
            • Persistent memory
            • Command system
            
            Experience the future of AI interaction! 🚀
        `);
    }
    
    showTime() {
        return `🕐 **Current time:** ${new Date().toLocaleTimeString()}`;
    }
    
    showDate() {
        return `📅 **Today's date:** ${new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`;
    }
    
    clearChat() {
        if (window.chat) {
            window.chat.clearChat();
            return "✨ Chat cleared! Ready for a fresh conversation. 🚀";
        }
        return "⚠️ Unable to clear chat.";
    }
    
    toggleTheme() {
        if (window.themeManager) {
            window.themeManager.toggle();
            return "🎨 Theme toggled!";
        }
        return "⚠️ Theme manager not available.";
    }
    
    showStats() {
        const stats = window.prabeshAI?.getStats() || {};
        return this.formatResponse(`
            📊 **System Statistics — Prabesh Core**
            
            • **Total Interactions:** ${stats.totalInteractions || 0}
            • **Avg Response Time:** ${stats.averageResponseTime || 0}ms
            • **Memory Size:** ${stats.memorySize || 0} entries
            • **AI Status:** Active
            • **Creator:** Prabesh Paudel
            
            All systems operational! ✅
        `);
    }
    
    exportChat() {
        if (window.chat) {
            const messages = JSON.stringify(window.chat.messages, null, 2);
            const blob = new Blob([messages], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `astravox-chat-${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(url);
            return "📥 Chat exported successfully!";
        }
        return "⚠️ Unable to export chat.";
    }
    
    toggleVoice() {
        if (window.voiceAI) {
            window.voiceAI.toggle();
            return window.voiceAI.isListening ? "🎤 Voice mode activated!" : "🎤 Voice mode deactivated.";
        }
        return "⚠️ Voice AI not available.";
    }
    
    formatResponse(text) {
        return text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }
    
    getCommandHistory() {
        return this.commandHistory;
    }
}

window.commandSystem = new CommandSystem();