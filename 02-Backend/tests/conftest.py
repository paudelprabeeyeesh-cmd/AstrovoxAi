import pytest
from app.database import init_db
import os

DB_PATH = os.getenv("ASTROVOX_DB", "astrovox.db")


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    if os.getenv("DATABASE_URL"):
        init_db()
    yield
    for ext in ["", "-shm", "-wal"]:
        p = DB_PATH + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except PermissionError:
                pass
