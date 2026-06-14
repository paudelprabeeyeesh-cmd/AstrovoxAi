const express = require("express");
const cors = require("cors");
const Database = require("better-sqlite3");
const app = express();
const PORT = 5000;

const db = new Database("astravox.db");
db.exec("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT)");

app.use(cors());
app.use(express.json());
app.use(express.static("public"));

app.get("/health", (req, res) => {
    const count = db.prepare("SELECT COUNT(*) as c FROM messages").get().c;
    res.json({ status: "online", messages: count });
});

app.post("/api/chat", (req, res) => {
    const { message } = req.body;
    const lowerMsg = message.toLowerCase();
    
    db.prepare("INSERT INTO messages (role, content) VALUES (?, ?)").run("user", message);
    
    let reply = "";
    
    if (lowerMsg.includes("who created you") || lowerMsg.includes("who made you") || lowerMsg.includes("your creator")) {
        reply = `🧠 **ASTRAVOX-AI Development Team** 🧠\n\n` +
                `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
                `🎯 **AI Architecture & Vision**\n` +
                `   👨‍💻 Prabesh Paudel\n` +
                `   (Main AI Architect & Creator)\n\n` +
                `⚙️ **Backend Development**\n` +
                `   👨‍💻 Dipson Baral\n` +
                `   (Database, API & Server Logic)\n\n` +
                `🎨 **Frontend Development**\n` +
                `   👨‍💻 Susanta Baral\n` +
                `   (UI/UX, 3D Graphics & Interface)\n` +
                `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
                `✨ ASTRAVOX-AI is a premium cognitive engine built with passion! ✨`;
    }
    else if (lowerMsg.includes("prabesh")) {
        reply = `👨‍💻 **Prabesh Paudel** - Main AI Architect & Creator of ASTRAVOX-AI\n\nHe designed the core cognitive architecture and AI reasoning engine. His vision made ASTRAVOX-AI possible! 🚀`;
    }
    else if (lowerMsg.includes("dipson")) {
        reply = `⚙️ **Dipson Baral** - Backend Developer\n\nHe built the robust backend infrastructure, SQLite database integration, API endpoints, and server logic! 💾`;
    }
    else if (lowerMsg.includes("susanta")) {
        reply = `🎨 **Susanta Baral** - Frontend Developer\n\nHe created the beautiful glassmorphic UI and smooth animations you're experiencing! ✨`;
    }
    else if (lowerMsg.includes("help")) {
        reply = `📚 **Commands:**\n• "Who created you?" - Meet developers\n• "Prabesh" - About AI Architect\n• "Dipson" - About Backend\n• "Susanta" - About Frontend\n• "Stats" - System info`;
    }
    else if (lowerMsg.includes("stats")) {
        const count = db.prepare("SELECT COUNT(*) as c FROM messages").get().c;
        reply = `📊 **Statistics:**\n• Messages: ${count}\n• Database: SQLite\n• Status: Active\n\nBuilt by Prabesh, Dipson & Susanta!`;
    }
    else {
        reply = `🧠 ASTRAVOX-AI: "${message}"\n\nAsk me "Who created you?" to meet my developers - Prabesh Paudel, Dipson Baral & Susanta Baral!`;
    }
    
    db.prepare("INSERT INTO messages (role, content) VALUES (?, ?)").run("assistant", reply);
    res.json({ response: reply });
});

app.listen(PORT, () => {
    console.log(`\n╔════════════════════════════════════════════╗`);
    console.log(`║     🧠 ASTRAVOX-AI IS RUNNING!            ║`);
    console.log(`╠════════════════════════════════════════════╣`);
    console.log(`║  URL: http://localhost:${PORT}              ║`);
    console.log(`║  Created by: Prabesh, Dipson & Susanta    ║`);
    console.log(`╚════════════════════════════════════════════╝\n`);
});