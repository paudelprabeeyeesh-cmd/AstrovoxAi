// ============================================
// PRABESH PAUDEL — BACKEND SERVER
// Backend Engineer | Database Manager | API Developer
// ============================================

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const WebSocket = require('ws');
const http = require('http');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Security Middleware
app.use(helmet());
app.use(cors());
app.use(compression());
app.use(express.json({ limit: '10mb' }));

// Rate Limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    message: 'Too many requests, please try again later.'
});
app.use('/api/', limiter);

// Database Connection (SQLite)
const Database = require('better-sqlite3');
const db = new Database('astravox.db');

// Initialize Database
db.exec(`
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER,
        role TEXT,
        content TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
`);

// API Routes
app.get('/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        version: '3.0.0',
        creator: 'Prabesh Paudel'
    });
});

app.post('/api/chat', async (req, res) => {
    const { message, conversationId } = req.body;
    
    try {
        // Save user message
        const saveUserMsg = db.prepare(`
            INSERT INTO messages (conversation_id, role, content) 
            VALUES (?, 'user', ?)
        `);
        saveUserMsg.run(conversationId || 1, message);
        
        // Generate AI response
        const response = await generateAIResponse(message);
        
        // Save AI response
        const saveAIRsp = db.prepare(`
            INSERT INTO messages (conversation_id, role, content) 
            VALUES (?, 'assistant', ?)
        `);
        saveAIRsp.run(conversationId || 1, response);
        
        res.json({ response, success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/conversations', (req, res) => {
    const conversations = db.prepare(`
        SELECT * FROM conversations ORDER BY created_at DESC
    `).all();
    res.json(conversations);
});

app.get('/api/messages/:conversationId', (req, res) => {
    const messages = db.prepare(`
        SELECT * FROM messages 
        WHERE conversation_id = ? 
        ORDER BY created_at ASC
    `).all(req.params.conversationId);
    res.json(messages);
});

function generateAIResponse(message) {
    const msg = message.toLowerCase();
    
    if (msg.includes('who created you') || msg.includes('prabesh')) {
        return `🧠 I was created by Prabesh Paudel — Founder, Lead Developer & Chief AI Architect of AstraVox AI! 🚀`;
    }
    
    if (msg.includes('hello') || msg.includes('hi')) {
        return `👋 Hello! I'm ASTRAVOX-AI, created by Prabesh Paudel. How can I help you today?`;
    }
    
    if (msg.includes('help')) {
        return `📚 Commands: /help, /clear, /theme, /stats, /export, /voice — Try "Who created you?" to meet my creator!`;
    }
    
    return `💡 I understand: "${message}" — Ask me "Who created you?" to learn about Prabesh Paudel!`;
}

// WebSocket Server
wss.on('connection', (ws) => {
    console.log('Client connected');
    
    ws.on('message', (data) => {
        const message = data.toString();
        wss.clients.forEach(client => {
            if (client !== ws && client.readyState === WebSocket.OPEN) {
                client.send(message);
            }
        });
    });
    
    ws.on('close', () => console.log('Client disconnected'));
});

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
    console.log(`
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║     🧠 ASTRAVOX-AI BACKEND SERVER — PRABESH PAUDEL              ║
    ║                                                                  ║
    ║     📍 URL: http://localhost:${PORT}                               ║
    ║     👑 Creator: Prabesh Paudel                                   ║
    ║     🎯 Role: Backend Engineer & Database Manager                 ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    `);
});