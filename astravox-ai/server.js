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
    db.prepare("INSERT INTO messages (role, content) VALUES (?, ?)").run("user", message);
    const reply = "🧠 ASTRAVOX-AI: " + message;
    db.prepare("INSERT INTO messages (role, content) VALUES (?, ?)").run("assistant", reply);
    res.json({ response: reply });
});

app.listen(PORT, () => console.log("ASTRAVOX-AI running on http://localhost:" + PORT));
