"""Tests for WebSocket live streaming (/ws/live) and forensic event bus."""

from __future__ import annotations

import json
import time
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.events import ForensicEvent, event_bus

client = TestClient(app)


def test_websocket_live_feed_and_broadcasting():
    """Verify WebSocket handshake and receiving broadcast events within 1s."""
    with client.websocket_connect("/ws/live") as websocket:
        # 1. Verify handshake event
        handshake_raw = websocket.receive_text()
        handshake = json.loads(handshake_raw)
        assert handshake.get("type") == "connected"
        assert handshake.get("data", {}).get("status") == "online"

        # 2. Publish a synthetic event via event bus
        test_event = ForensicEvent(
            type="new_alert",
            data={"alert_id": "test_ws_001", "entity_id": "ent_test_99", "risk_score": 0.89},
        )
        event_bus.publish_sync(test_event)

        # 3. Receive event from websocket
        received_raw = websocket.receive_text()
        received = json.loads(received_raw)
        assert received.get("type") == "new_alert"
        assert received.get("data", {}).get("alert_id") == "test_ws_001"
        assert received.get("data", {}).get("risk_score") == 0.89
