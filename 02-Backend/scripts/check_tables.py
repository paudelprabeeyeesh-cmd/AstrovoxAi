import os
os.environ.setdefault('DATABASE_URL', 'sqlite:///test.db')
os.environ.setdefault('ASTROVOX_DB', 'test.db')
from app.database import init_db, get_db
init_db()
with get_db() as conn:
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print('Tables:', [t['name'] for t in tables])
