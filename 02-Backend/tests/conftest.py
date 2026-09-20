import os

os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("ASTROVOX_DB", "test.db")
os.environ.setdefault("ASTROVOX_TEST_MODE", "1")
if not os.getenv("ASTROVOX_ENCRYPTION_KEY"):
    os.environ["ASTROVOX_ENCRYPTION_KEY"] = "HSMTYGgSppCPt3g3VAorkpAX4GR0W8T3ILpsKLfblns="

import pytest
from app.database import init_db
from app.main import app
from fastapi.testclient import TestClient

DB_PATH = os.environ.get("ASTROVOX_DB", "test.db")

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()
    yield
    for ext in ["", "-shm", "-wal"]:
        p = DB_PATH + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except PermissionError:
                pass
