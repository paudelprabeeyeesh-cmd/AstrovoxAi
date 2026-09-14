import pytest
from app.database import init_db
import os

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()
    yield
    db_path = os.getenv("ASTROVOX_DB", "astrovox.db")
    if os.path.exists(db_path):
        os.remove(db_path)
