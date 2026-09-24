"""Auth flow integration tests through FastAPI TestClient."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app import auth as auth_module
from app import database as db_module


class FakeSupabaseAuth:
    def __init__(self, fake):
        self._fake = fake

    def sign_up(self, payload):
        user_id = f"user-{self._fake._next_profile_id}"
        self._fake._next_profile_id += 1
        user = MagicMock()
        user.id = user_id
        user.email = payload.get("email")
        session = MagicMock()
        session.access_token = f"access-{user_id}"
        session.refresh_token = f"refresh-{user_id}"
        response = MagicMock()
        response.user = user
        response.session = session
        return response

    def sign_in_with_password(self, payload):
        return self.sign_up(payload)

    def get_user(self, token):
        user_id = token.replace("Bearer ", "").replace("access-", "")
        user = MagicMock()
        user.id = f"user-{user_id}"
        user.email = f"user{user_id}@test.com"
        user.app_metadata = {"roles": ["user"]}
        response = MagicMock()
        response.user = user
        return response

    def refresh_session(self, token):
        session = MagicMock()
        session.access_token = f"new-access-{token}"
        session.refresh_token = f"new-refresh-{token}"
        response = MagicMock()
        response.session = session
        return response

    def reset_password_for_email(self, email, options=None):
        return MagicMock()

    def sign_in_with_otp(self, payload):
        return MagicMock()


class FakeSupabaseTable:
    def __init__(self, fake, name):
        self._fake = fake
        self._name = name
        self._filters = []
        self._insert_data = None
        self._update_data = None
        self._order_field = None
        self._order_desc = False
        self._limit_val = None
        self._range_start = None
        self._range_end = None

    def insert(self, data):
        self._insert_data = data
        return self

    def select(self, columns="*"):
        self._select_columns = columns
        return self

    def eq(self, field, value):
        self._filters.append(("eq", field, value))
        return self

    def update(self, data):
        self._update_data = data
        return self

    def delete(self):
        self._delete_mode = True
        return self

    def order(self, field, desc=False):
        self._order_field = field
        self._order_desc = desc
        return self

    def limit(self, n):
        self._limit_val = n
        return self

    def range(self, start, end):
        self._range_start = start
        self._range_end = end
        return self

    def execute(self):
        table = self._fake._data.setdefault(self._name, [])
        if self._insert_data is not None:
            record = dict(self._insert_data)
            record_id = self._fake._next_ids.get(self._name, 1)
            record["id"] = record_id
            self._fake._next_ids[self._name] = record_id + 1
            table.append(record)
            response = MagicMock()
            response.data = [record]
            return response
        if self._update_data is not None:
            for row in table:
                match = True
                for op, field, value in self._filters:
                    if op == "eq" and row.get(field) != value:
                        match = False
                        break
                if match:
                    row.update(self._update_data)
            response = MagicMock()
            response.data = [row for row in table if all(
                (row.get(f) == v) for op, f, v in self._filters if op == "eq"
            )]
            return response
        if getattr(self, "_delete_mode", False):
            deleted = []
            new_table = []
            for row in table:
                match = all(
                    (row.get(f) == v) for op, f, v in self._filters if op == "eq"
                )
                if match:
                    deleted.append(row)
                else:
                    new_table.append(row)
            self._fake._data[self._name] = new_table
            response = MagicMock()
            response.data = deleted
            return response
        results = list(table)
        for op, field, value in self._filters:
            if op == "eq":
                results = [row for row in results if row.get(field) == value]
        if self._order_field:
            results.sort(key=lambda r: r.get(self._order_field, ""), reverse=self._order_desc)
        if self._range_start is not None:
            end = self._range_end + 1 if self._range_end is not None else None
            results = results[self._range_start:end]
        elif self._limit_val is not None:
            results = results[: self._limit_val]
        response = MagicMock()
        response.data = results
        return response


class FakeSupabase:
    def __init__(self):
        self._data = {}
        self._next_ids = {}
        self._next_profile_id = 1

    def table(self, name):
        return FakeSupabaseTable(self, name)

    @property
    def auth(self):
        return FakeSupabaseAuth(self)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_supabase():
    return FakeSupabase()


@pytest.fixture(autouse=True)
def mock_supabase(fake_supabase):
    with patch.object(auth_module, "supabase", fake_supabase), \
         patch.object(db_module, "supabase", fake_supabase):
        yield fake_supabase


class TestAuthFlow:
    def test_signup_returns_user_and_session(self, client, mock_supabase):
        response = client.post("/auth/signup", json={
            "email": "newuser@test.com",
            "password": "SecurePass1!",
            "full_name": "New User",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "user" in data
        assert data["user"]["email"] == "newuser@test.com"

    def test_login_returns_session(self, client, mock_supabase):
        response = client.post("/auth/login", json={
            "email": "user@test.com",
            "password": "password123",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "access_token" in data.get("session", {})

    def test_signup_validation_requires_email(self, client):
        response = client.post("/auth/signup", json={
            "password": "SecurePass1!",
            "full_name": "Test",
        })
        assert response.status_code == 422

    def test_signup_validation_requires_password(self, client):
        response = client.post("/auth/signup", json={
            "email": "test@test.com",
            "full_name": "Test",
        })
        assert response.status_code == 422

    def test_login_validation_requires_email(self, client):
        response = client.post("/auth/login", json={
            "password": "SecurePass1!",
        })
        assert response.status_code == 422

    def test_login_validation_requires_password(self, client):
        response = client.post("/auth/login", json={
            "email": "test@test.com",
        })
        assert response.status_code == 422

    def test_logout_always_succeeds(self, client):
        response = client.post("/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    def test_reset_password(self, client, mock_supabase):
        response = client.post("/auth/reset-password", json={
            "email": "user@test.com",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    def test_me_requires_auth_header(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_me_with_token_returns_user(self, client, mock_supabase):
        response = client.get("/auth/me?authorization=Bearer access-1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "user" in data

    def test_refresh_token(self, client, mock_supabase):
        response = client.post("/auth/refresh?refresh_token=valid-refresh-token")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "access_token" in data.get("session", {})

    def test_oauth_initiates_flow(self, client, mock_supabase):
        response = client.post("/auth/oauth", json={
            "provider": "google",
            "access_token": "fake-oauth-token",
            "email": "oauth@test.com",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert data["provider"] == "google"
