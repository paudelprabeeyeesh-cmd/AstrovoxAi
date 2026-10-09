from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.chat import router as chat_router


def test_create_conversation():
    app = FastAPI()
    app.include_router(chat_router)
    client = TestClient(app)

    response = client.post("/conversations")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert "conversation" in body


def test_send_message():
    app = FastAPI()
    app.include_router(chat_router)
    client = TestClient(app)

    conv = client.post("/conversations").json()
    conv_id = conv["conversation"]["id"]

    response = client.post("/message", json={"conversation_id": conv_id, "content": "Hello"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "user"
    assert body["content"] == "Hello"


def test_get_messages_not_found():
    app = FastAPI()
    app.include_router(chat_router)
    client = TestClient(app)

    response = client.get("/conversations/unknown/messages")
    assert response.status_code == 404


def test_list_models():
    app = FastAPI()
    app.include_router(chat_router)
    client = TestClient(app)

    response = client.get("/models")
    assert response.status_code == 200
    body = response.json()
    assert "models" in body
