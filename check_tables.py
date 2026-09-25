import sqlite3, os
p = os.path.join("02-Backend", "database", "chat.db")
conn = sqlite3.connect(p)
rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print([r[0] for r in rows])
conn.close()
