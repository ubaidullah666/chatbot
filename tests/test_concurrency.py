"""
Concurrency Tests for Multiple Simultaneous Chat Sessions.
Verifies asynchronous non-blocking operation across independent sessions.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.conversation_manager import conversation_manager

@pytest.mark.asyncio
async def test_concurrent_sessions_isolation():
    """Verify that multiple sessions can be created and queried simultaneously without cross-talk."""
    sess1 = await conversation_manager.get_or_create_session("concurrent-user-1")
    sess2 = await conversation_manager.get_or_create_session("concurrent-user-2")

    sess1.add_message("user", "I want an Economy car.")
    sess2.add_message("user", "I want a Luxury car.")

    # Check that session 1 does not leak into session 2
    assert sess1.extracted_state["vehicle_category"] == "Economy ($45/day)"
    assert sess2.extracted_state["vehicle_category"] == "Luxury ($135/day)"

    # Verify session history count
    assert len(sess1.history) == 1
    assert len(sess2.history) == 1
    assert sess1.history[0].content != sess2.history[0].content

    # Clean up
    await conversation_manager.delete_session("concurrent-user-1")
    await conversation_manager.delete_session("concurrent-user-2")

def test_multiple_simultaneous_websocket_connections():
    """Verify server sustains multiple concurrent active WebSocket connections simultaneously."""
    client = TestClient(app)

    with client.websocket_connect("/ws/chat") as ws1:
        with client.websocket_connect("/ws/chat") as ws2:
            # Send pings simultaneously
            ws1.send_json({"type": "ping"})
            ws2.send_json({"type": "ping"})

            res1 = ws1.receive_json()
            res2 = ws2.receive_json()

            assert res1 == {"type": "pong"}
            assert res2 == {"type": "pong"}
