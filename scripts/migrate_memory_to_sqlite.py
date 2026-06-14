#!/usr/bin/env python3
import os
import json
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_FILE = os.path.join(ROOT, 'AI-Integration', 'ai-logic', 'chat_history_db.json')
DB_FILE = os.path.join(ROOT, '02-Backend', 'database', 'chat.db')

if not os.path.exists(MEMORY_FILE):
    print('No memory file found:', MEMORY_FILE)
    raise SystemExit(1)

with open(MEMORY_FILE, 'r', encoding='utf-8') as fh:
    data = json.load(fh)

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT,
    user_id TEXT,
    role TEXT,
    message TEXT,
    created_at TEXT
)''')
conn.commit()

count = 0
for conv_id, turns in data.items():
    for turn in turns:
        role = turn.get('role')
        message = turn.get('message')
        ts = turn.get('timestamp') or turn.get('created_at') or ''
        user_id = 'migrated'
        cur.execute('INSERT INTO chats (conversation_id, user_id, role, message, created_at) VALUES (?,?,?,?,?)', (conv_id, user_id, role, message, ts))
        count += 1

conn.commit()
conn.close()
print(f'Migrated {count} messages into {DB_FILE}')
