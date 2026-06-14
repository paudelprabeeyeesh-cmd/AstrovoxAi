// ============================================
// DEEPSEEK API INTEGRATION
// ASTRAVOX-AI — Real AI Intelligence
// API Key: sk-4cb4a87bed78488c990e07efcbe7e8a7
// ============================================

const DEEPSEEK_API_KEY = 'sk-4cb4a87bed78488c990e07efcbe7e8a7';
const DEEPSEEK_URL = 'https://api.deepseek.com/v1/chat/completions';

let totalAPICalls = 0;

async function callDeepSeekAPI(userMessage) {
    try {
        totalAPICalls++;
        updateStats();
        
        const response = await fetch(DEEPSEEK_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${DEEPSEEK_API_KEY}`
            },
            body: JSON.stringify({
                model: 'deepseek-chat',
                messages: [
                    {
                        role: 'system',
                        content: `You are ASTRAVOX-AI, a premium cognitive assistant created by:
- Prabesh Paudel (AI Architect & Creator)
- Dipson Baral (Backend Developer & Database Engineer)
- Susanta Baral (Frontend Developer & UI Artist)

Answer questions clearly, accurately, and helpfully. When asked about creators, proudly mention all three developers equally.`
                    },
                    {
                        role: 'user',
                        content: userMessage
                    }
                ],
                temperature: 0.7,
                max_tokens: 2000
            })
        });
        
        const data = await response.json();
        
        if (data.choices && data.choices[0]) {
            return data.choices[0].message.content;
        } else if (data.error) {
            console.error('DeepSeek API Error:', data.error);
            return getLocalResponse(userMessage);
        }
        
        return getLocalResponse(userMessage);
        
    } catch (error) {
        console.error('DeepSeek API Error:', error);
        return getLocalResponse(userMessage);
    }
}

function getLocalResponse(question) {
    const q = question.toLowerCase();
    
    if (q.includes('who created you') || q.includes('who made you')) {
        return `🧠 ASTRAVOX-AI was created by:\n\n🎯 Prabesh Paudel — AI Architect & Creator\n⚙️ Dipson Baral — Backend Developer\n🎨 Susanta Baral — Frontend Developer\n\nTogether they built this cognitive engine! 🚀`;
    }
    if (q.includes('prabesh')) return `🎯 Prabesh Paudel — AI Architect & Creator. He designed the core AI architecture!`;
    if (q.includes('dipson')) return `⚙️ Dipson Baral — Backend Developer. He built the database and server systems!`;
    if (q.includes('susanta')) return `🎨 Susanta Baral — Frontend Developer. He created this beautiful interface!`;
    if (q.includes('hello') || q.includes('hi')) return `👋 Hello! I'm ASTRAVOX-AI, powered by DeepSeek. Ask me "Who created you?" to meet my developers!`;
    if (q.includes('help')) return `📚 Commands: "Who created you?", "Prabesh", "Dipson", "Susanta", "Help"`;
    
    return `💡 I understand your question. Ask me "Who created you?" to learn about my developers — Prabesh Paudel, Dipson Baral & Susanta Baral! 🚀`;
}

function updateStats() {
    const msgElements = document.querySelectorAll('#statMessages, #dashMessages, #analyticsMessages, #msgCount');
    msgElements.forEach(el => { if(el) el.innerText = messageCount || 0; });
    
    const callElements = document.querySelectorAll('#statCalls, #dashCalls, #analyticsCalls');
    callElements.forEach(el => { if(el) el.innerText = totalAPICalls; });
    
    const mem = Math.round(performance.memory?.usedJSHeapSize / 1048576 || 0);
    const memElements = document.querySelectorAll('#statMemory, #dashMemory, #analyticsMemory');
    memElements.forEach(el => { if(el) el.innerText = mem; });
}