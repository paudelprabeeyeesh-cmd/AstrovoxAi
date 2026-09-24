
import os
import hashlib
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestVisualRegression:
    def test_home_page_checksum_stable(self):
        response = client.get("/")
        assert response.status_code == 200
        html = response.text
        checksum = hashlib.sha256(html.encode("utf-8")).hexdigest()
        snapshot_path = Path("tests") / "snapshots" / "home_page.sha256"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        if snapshot_path.exists():
            stored = snapshot_path.read_text().strip()
            assert checksum == stored, "Home page visual regression detected"
        else:
            snapshot_path.write_text(checksum)

    def test_health_page_checksum_stable(self):
        response = client.get("/health")
        assert response.status_code == 200
        html = response.text
        checksum = hashlib.sha256(html.encode("utf-8")).hexdigest()
        snapshot_path = Path("tests") / "snapshots" / "health_page.sha256"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        if snapshot_path.exists():
            stored = snapshot_path.read_text().strip()
            assert checksum == stored, "Health page visual regression detected"
        else:
            snapshot_path.write_text(checksum)

    def test_known_html_contains_expected_chunks(self):
        response = client.get("/")
        assert response.status_code == 200
        html = response.text.lower()
        assert "<!doctype html>" in html or "<html" in html

    def test_no_unhandled_exception_in_render(self):
        response = client.get("/")
        assert response.status_code != 500
