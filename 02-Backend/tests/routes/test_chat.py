from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.chat import router as chat_router, conversations_store, messages_store


def _reset_chat_stores():
    conversations_store.clear()
    messages_store.clear()


def test_create_conversation():
    _reset_chat_stores()
    app = FastAPI()
    app.include_router(chat_router)
    client = TestClient(app)

    response = client.post("/conversations", params={"user_id": "u1"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert "conversation" in body
    assert body["conversation"]["title"] == "New conversation"
    assert body["conversation"]["user_id"] == "u1"


def test_create_conversation_no_user():
    _reset_chat_stores()
    app = FastAPI()
    app.include_router(chat_router)
    client = TestClient(app)

    response = client.post("/conversations")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert body["conversation"]["user_id"] is None


def test_get_messages_empty():
    _reset_chat_stores()
    app = FastAPI()
    app.include_router(chat_router)
    client = TestClient(app)

    response = client.get("/conversations/missing/messages")
    assert response.status_code == 404


def test_send_message():
    _reset_chat_stores()
    app = FastAPI()
    app.include_router(chat_router)
    client = TestClient(app)

    client.post("/conversations", params={"user_id": "u1"})
    conv_id = list(conversations_store.keys())[0]

    payload = {"conversation_id": conv_id, "role": "user", "content": "Hello"}
    response = client.post("/message", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] == conv_id
    assert body["role"] == "user"
    assert body["content"] == "Hello"
    assert "id" in body
    assert "created_at" in body


def test_send_message_missing_conversation():
    _reset_chat_stores()
    app = FastAPI()
    app.include_router(chat_router)
    client = TestClient(app)

    payload = {"conversation_id": "missing", "role": "user", "content": "Hi"}
    response = client.post("/message", json=payload)
    assert response.status_code == 404


def test_list_chat_models():
    _reset_chat_stores()
    app = FastAPI()
    app.include_router(chat_router)
    client = TestClient(app)

    response = client.get("/models")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert len(body["models"]) == 2


def test_get_messages_with_messages():
    _reset_chat_stores()
    app = FastAPI()
    app.include_router(chat_router)
    client = TestClient(app)

    client.post("/conversations", params={"user_id": "u1"})
    conv_id = list(conversations_store.keys())[0]

    client.post("/message", json={"conversation_id": conv_id, "role": "user", "content": "Hello"})
    client.post("/message", json={"conversation_id": conv_id, "role": "assistant", "content": "Hi there"})

    response = client.get(f"/conversations/{conv_id}/messages")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert body["count"] == 2
    assert len(body["messages"]) == 2
    assert body["messages"][0]["content"] == "Hello"
    assert body["messages"][1]["content"] == "Hi there"
