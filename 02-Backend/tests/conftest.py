import pytest
from app.database import init_db
import os

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()
    yield
    db_path = os.getenv("ASTROVOX_DB", "astrovox.db")
    for ext in ["", "-shm", "-wal"]:
        p = db_path + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except PermissionError:
                pass
