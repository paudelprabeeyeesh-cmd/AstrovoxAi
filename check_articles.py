import sqlite3, os
p = os.path.join("02-Backend", "database", "chat.db")
conn = sqlite3.connect(p)
rows = conn.execute("SELECT slug, title FROM help_articles LIMIT 5").fetchall()
print(rows)
conn.close()
