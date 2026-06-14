
// ============================================
// ASTRAVOX PRIME — AI ROUTING ENGINE
// Multi-Model Orchestration System
// Created by: Prabesh Paudel, Dipson Baral, Susanta AI
// ============================================

class AIRouter {
    constructor() {
        this.models = {
            deepseek: { name: "DeepSeek", active: true, priority: 1 },
            gemini: { name: "Gemini", active: false, priority: 2, apiKey: null },
            openai: { name: "OpenAI", active: false, priority: 3, apiKey: null },
            claude: { name: "Claude", active: false, priority: 4, apiKey: null }
        };
        this.currentModel = "deepseek";
        this.fallbackChain = ["deepseek", "gemini", "openai", "claude"];
    }
    
    async routeQuery(query, taskType = "general") {
        // Determine best model based on task type
        let selectedModel = this.selectModelForTask(taskType);
        
        for (let model of this.fallbackChain) {
            if (this.models[model].active) {
                try {
                    const response = await this.callModel(model, query);
                    if (response && !response.includes("error")) {
                        return { response, model, success: true };
                    }
                } catch (error) {
                    console.warn(`${model} failed:`, error);
                    continue;
                }
            }
        }
        
        // Fallback to local AI
        return { 
            response: aiEngine.generateResponse(query), 
            model: "local", 
            success: true 
        };
    }
    
    selectModelForTask(taskType) {
        const taskModelMap = {
            coding: "deepseek",
            reasoning: "claude",
            creative: "gemini",
            general: "deepseek",
            math: "deepseek",
            science: "gemini"
        };
        return taskModelMap[taskType] || "deepseek";
    }
    
    async callModel(modelName, query) {
        if (modelName === "deepseek") {
            return await this.callDeepSeek(query);
        }
        if (modelName === "gemini") {
            return await this.callGemini(query);
        }
        if (modelName === "openai") {
            return await this.callOpenAI(query);
        }
        if (modelName === "claude") {
            return await this.callClaude(query);
        }
        return null;
    }
    
    async callDeepSeek(query) {
        try {
            const response = await fetch('https://api.deepseek.com/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('deepseek_key') || ''}`
                },
                body: JSON.stringify({
                    model: 'deepseek-chat',
                    messages: [{ role: 'user', content: query }],
                    temperature: 0.7,
                    max_tokens: 800
                })
            });
            const data = await response.json();
            if (data.choices && data.choices[0]) {
                return data.choices[0].message.content;
            }
            return null;
        } catch (error) {
            return null;
        }
    }
    
    async callGemini(query) {
        // Gemini API integration (requires API key)
        return null;
    }
    
    async callOpenAI(query) {
        // OpenAI API integration (requires API key)
        return null;
    }
    
    async callClaude(query) {
        // Claude API integration (requires API key)
        return null;
    }
    
    setAPIKey(model, key) {
        if (this.models[model]) {
            this.models[model].apiKey = key;
            this.models[model].active = true;
            localStorage.setItem(`${model}_key`, key);
        }
    }
}

const aiRouter = new AIRouter();
window.aiRouter = aiRouter;