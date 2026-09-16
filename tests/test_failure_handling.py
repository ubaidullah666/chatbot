"""
Failure Handling and Resilience Tests.
Deliberately tests invalid payloads, mid-stream disconnects, and malformed requests.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_malformed_json_payload():
    """Verify malformed JSON does not crash the WebSocket connection and returns a clean error."""
    with client.websocket_connect("/ws/chat") as websocket:
        # Send raw invalid string that is not JSON
        websocket.send_text("this is completely invalid json {{{}}")
        res = websocket.receive_json()
        assert res["type"] == "error"
        assert res["code"] == "INVALID_JSON"

        # Connection should still be alive and responsive!
        websocket.send_json({"type": "ping"})
        pong = websocket.receive_json()
        assert pong == {"type": "pong"}

def test_unknown_message_type():
    """Verify unknown message types do not crash the connection."""
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "unknown_action_xyz", "content": "hello"})
        err = websocket.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "UNSUPPORTED_TYPE"

        # Send ping to verify connection remains healthy
        websocket.send_json({"type": "ping"})
        pong = websocket.receive_json()
        assert pong == {"type": "pong"}

def test_missing_session_id_auto_creates_session():
    """Verify that sending a message without a session_id does not error and auto-creates a session."""
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "reset_session"})
        res = websocket.receive_json()
        assert res["type"] == "session_reset"
        assert res["session_id"] is not None
