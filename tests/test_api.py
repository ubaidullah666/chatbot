"""
Unit & Integration Tests for ApexDrive REST and WebSocket API Endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_index_serves_html():
    """Verify that root endpoint serves the chat frontend HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "ApexDrive" in response.text
    assert "Car Rental" in response.text

def test_health_check():
    """Verify system health endpoint returns valid status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "model" in data
    assert "active_sessions" in data
    assert "uptime_seconds" in data

def test_domain_info():
    """Verify domain configuration metadata, fleet catalog, and policies."""
    response = client.get("/api/domain/info")
    assert response.status_code == 200
    data = response.json()
    assert "fleet" in data
    assert "Economy" in data["fleet"]
    assert "SUV" in data["fleet"]
    assert "Electric" in data["fleet"]
    assert "Luxury" in data["fleet"]
    assert "insurance" in data
    assert "policies" in data
    assert len(data["policies"]) >= 4

def test_session_lifecycle():
    """Verify session creation, retrieval, and reset."""
    # Create session
    create_res = client.post("/api/sessions")
    assert create_res.status_code == 200
    sess_data = create_res.json()
    session_id = sess_data["session_id"]
    assert session_id is not None
    assert "welcome_message" in sess_data

    # Retrieve session history
    get_res = client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 200
    history_data = get_res.json()
    assert history_data["session_id"] == session_id
    assert history_data["message_count"] == 1
    assert history_data["history"][0]["role"] == "assistant"

    # Reset session
    reset_res = client.post(f"/api/sessions/{session_id}/reset")
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["status"] == "success"

def test_websocket_ping_pong():
    """Verify WebSocket handshake and heartbeat ping/pong."""
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "ping"})
        data = websocket.receive_json()
        assert data == {"type": "pong"}

def test_websocket_empty_message_error():
    """Verify that sending empty user content returns a clean error, not a crash."""
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "user_message", "content": "   "})
        data = websocket.receive_json()
        assert data["type"] == "error"
        assert data["code"] == "EMPTY_CONTENT"

def test_websocket_session_reset():
    """Verify in-stream session reset over WebSocket."""
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "reset_session"})
        data = websocket.receive_json()
        assert data["type"] == "session_reset"
        assert "welcome_message" in data
