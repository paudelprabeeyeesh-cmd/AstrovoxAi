import pytest
import importlib
import time
import uuid
from fastapi.testclient import TestClient
from app.database import init_db, get_db

client = TestClient(importlib.import_module('app.main').app)


def _register():
    init_db()
    email = f"advanced-{int(time.time())}-{uuid.uuid4().hex[:6]}@test.com"
    r = client.post("/auth/register", json={"email": email, "password": "testpass123"})
    assert r.status_code == 200, r.text
    with get_db() as conn:
        conn.execute("UPDATE users SET email_verified = 1 WHERE email = ?", (email,))
        conn.commit()
    r = client.post("/auth/login", json={"email": email, "password": "testpass123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"], r.json()["user_id"]


def test_finetuning_jobs_endpoint():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/finetuning/jobs",
        json={"model": "gpt-4o-mini", "training_file": "file-abc123"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["model"] == "gpt-4o-mini"
    assert data["status"] == "queued"


def test_mcp_tools_register():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/mcp/tools",
        json={"name": "test_tool", "description": "A test tool", "config": {"url": "http://localhost:8000"}},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["name"] == "test_tool"


def test_mcp_tools_list():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/mcp/tools", json={"name": "test_tool_2", "description": "Another test"}, headers=headers)
    response = client.get("/mcp/tools", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_knowledge_graph_entities():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/knowledge-graph/entities",
        json={"entity_type": "concept", "name": "AI", "properties": {"domain": "computer science"}},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "AI"
    assert data["entity_type"] == "concept"


def test_analytics_dashboard():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/analytics/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_messages" in data
    assert "total_cost_usd" in data


def test_safety_moderation():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/safety/moderate", json={"content": "Hello, how are you?"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "scores" in data
    assert "blocked" in data


def test_safety_canary_token():
    from app.routers.safety_api import CANARY_TOKEN
    assert "CANARY" in CANARY_TOKEN


def test_multi_agent_orchestrate():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/agents/multi/orchestrate",
        json={"task": "Build a web app", "num_agents": 3},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "orchestration_id" in data
    assert len(data["agents"]) == 3


def test_plugin_marketplace_list():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/plugins", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_speculative_decoding():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/decoding/speculative",
        json={"prompt": "Hello world", "draft_model": "haiku-1b", "target_model": "haiku"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "accepted_tokens" in data
    assert "speedup_factor" in data


def test_memory_incognito():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/memory/store",
        json={"content": "test memory", "memory_type": "fact", "importance": 0.5, "incognito": True},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["incognito"] is True


def test_conversation_branching():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/conversation/branches",
        json={"parent_id": None, "name": "Test Branch"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["name"] == "Test Branch"


def test_templates_create():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/templates",
        json={"name": "Test Template", "content": "Hello {{name}}"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Template"


def test_workflow_create():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/workflows",
        json={"name": "Test Workflow", "steps": [{"id": 1, "action": "notify"}], "triggers": ["manual"]},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Workflow"


def test_rag_retrieval():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/rag/retrieval",
        json={"query": "What is AI?", "top_k": 10, "alpha": 0.7},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "final_results" in data
    assert data["method"] == "hybrid_rrf"


def test_paged_attention():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/inference/paged-attention/allocate",
        json={"seq_len": 2048, "page_size": 16},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "page_table" in data
    assert "num_pages" in data


def test_context_window_extension():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/context/extend",
        json={"base_seq_len": 32768, "target_seq_len": 1048576, "method": "yarn"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "yarn"
    assert data["stretch_factor"] == 8.0


def test_moe_routing():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    setup_resp = client.post("/moe/setup", json={"num_experts": 8, "top_k": 2}, headers=headers)
    assert setup_resp.status_code == 200
    run_id = setup_resp.json()["run_id"]
    route_resp = client.post(
        f"/moe/route?run_id={run_id}",
        json={"tokens": [{"embedding": [0.1] * 768, "content": "test"}]},
        headers=headers,
    )
    assert route_resp.status_code == 200
    data = route_resp.json()
    assert "routing_stats" in data


def test_model_versioning():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/models", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_model_distillation():
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/distillation/jobs", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
